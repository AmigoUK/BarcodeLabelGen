# F39 — Local (USB/system) Printers via Connector — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The connector discovers the OS print queues (CUPS on macOS/Linux, winspool on Windows) and prints raw ZPL to them, so a USB-attached printer (e.g. Zebra ZD421 on a Mac) shows up in BLG automatically — zero config.yaml editing.

**Architecture:** New printer kind `local` beside `tcp`/`file`. A `LocalPrinters` cache refreshes from the OS every 60 s; the heartbeat reports config printers + discovered queues (with a `kind` field) to `/api/agent/state`; print jobs still carry only a printer name — the connector resolves config first, discovered second. Backend adds an optional `kind` to the agent schema (no DB migration — `device.printers` is JSON). Frontend badges local printers in the print dialog and Devices page.

**Tech Stack:** Go 1.22 (connector, zero cgo — Windows via `github.com/alexbrainman/printer` syscall lib), Flask + Pydantic (backend), React + i18next (frontend).

## Global Constraints

- Connector stays **pure Go, zero cgo** — `connector/build-all.sh` matrix must keep building all six targets.
- No Alembic migration (spec: `device.printers` is a JSON column).
- Old connectors that don't send `kind` must keep working (schema default `"network"`).
- Print jobs keep their contract: `{id, printer, copies, zpl}` — name-only printer reference.
- Shell safety: never build a shell string; `exec.Command` with an args slice; queue names validated by `validQueueName`.
- All new UI strings in **both** `frontend/src/i18n/locales/pl.json` and `en.json`.
- Version bump at the end: app **v0.22.0** (minor), connector `Version` → **0.6.0**.
- Commit messages: `feat(scope): …` / `fix(scope): …`, each task commits separately, Co-Authored-By footer per repo convention.

---

### Task 1: Connector core — `Printer.Kind`, `kindForHost`, `validQueueName`, `LocalPrinters` cache

**Files:**
- Modify: `connector/config.go` (Printer struct, new consts + helper)
- Create: `connector/localprinters.go` (portable cache + validation)
- Test: `connector/localprinters_test.go`

**Interfaces:**
- Consumes: existing `Printer` struct (`connector/config.go:16`).
- Produces (used by Tasks 2–4):
  - `const KindNetwork = "network"; KindFile = "file"; KindLocal = "local"`
  - `func kindForHost(host string) string`
  - `func validQueueName(name string) bool`
  - `type LocalPrinters struct` with methods `Refresh()`, `Snapshot() []string`, `Has(name string) bool`
  - `Printer.Kind string` field (`yaml:"-" json:"kind"`)
  - `func mergedPrinters(cfg *Config, local []string) []Printer`
  - Note: `LocalPrinters.Refresh()` is **not** part of this task — it depends on
    the per-platform `listSystemPrinters()` and lands in Task 2. Here implement
    and test only `set(names)`, `Snapshot()`, `Has(name)`.

- [ ] **Step 1: Write the failing test**

Create `connector/localprinters_test.go`:

```go
package main

import "testing"

func TestValidQueueName(t *testing.T) {
	valid := []string{"Zebra_ZD421", "HP.LaserJet-2", "a", "Q+plus"}
	for _, n := range valid {
		if !validQueueName(n) {
			t.Errorf("validQueueName(%q) = false, want true", n)
		}
	}
	invalid := []string{"", "has space", "slash/name", "hash#name", "semi;colon",
		"dollar$", "back`tick", string(make([]byte, 200))}
	for _, n := range invalid {
		if validQueueName(n) {
			t.Errorf("validQueueName(%q) = true, want false", n)
		}
	}
}

func TestKindForHost(t *testing.T) {
	if got := kindForHost("file:///tmp/spool"); got != KindFile {
		t.Errorf("kindForHost(file://…) = %q, want %q", got, KindFile)
	}
	if got := kindForHost("192.168.1.50"); got != KindNetwork {
		t.Errorf("kindForHost(ip) = %q, want %q", got, KindNetwork)
	}
}

func TestLocalPrintersSnapshotAndHas(t *testing.T) {
	var l LocalPrinters
	l.set([]string{"Zebra_ZD421", "Office"})
	if !l.Has("Zebra_ZD421") || l.Has("Nope") {
		t.Fatal("Has() wrong")
	}
	snap := l.Snapshot()
	if len(snap) != 2 || snap[0] != "Zebra_ZD421" {
		t.Fatalf("Snapshot() = %v", snap)
	}
	snap[0] = "mutated" // must not affect internal state
	if !l.Has("Zebra_ZD421") {
		t.Fatal("Snapshot leaked internal slice")
	}
}

func TestMergedPrinters(t *testing.T) {
	cfg := &Config{Printers: []Printer{
		{Name: "drukarka", Host: "192.168.1.50", Port: 9100},
		{Name: "spool", Host: "file:///tmp/x"},
		{Name: "Zebra_ZD421", Host: "10.0.0.9", Port: 9100}, // YAML wins over discovered
	}}
	got := mergedPrinters(cfg, []string{"Zebra_ZD421", "Office"})
	if len(got) != 4 {
		t.Fatalf("len = %d, want 4 (3 config + 1 discovered)", len(got))
	}
	if got[0].Kind != KindNetwork || got[1].Kind != KindFile {
		t.Errorf("config kinds = %q,%q", got[0].Kind, got[1].Kind)
	}
	if got[2].Name != "Zebra_ZD421" || got[2].Kind != KindNetwork {
		t.Errorf("YAML printer must win the name clash: %+v", got[2])
	}
	last := got[3]
	if last.Name != "Office" || last.Kind != KindLocal || last.Port != 9100 {
		t.Errorf("discovered = %+v", last)
	}
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd connector && go test ./... -run 'TestValidQueueName|TestKindForHost|TestLocalPrinters|TestMergedPrinters' -v`
Expected: compile error — `validQueueName`, `KindFile`, `LocalPrinters`, `mergedPrinters` undefined.

- [ ] **Step 3: Implement**

In `connector/config.go`, extend the Printer struct and add the kind helper:

```go
// Printer is a print target. Host is an IP/hostname (RAW TCP, JetDirect),
// a `file:///path/to/dir` URL (spool-to-disk simulated printer), or empty
// for Kind==KindLocal — a system print queue discovered at runtime.
type Printer struct {
	Name string `yaml:"name" json:"name"`
	Host string `yaml:"host" json:"host"`
	Port int    `yaml:"port" json:"port"`
	// Kind is computed, never read from YAML: network | file | local.
	Kind string `yaml:"-" json:"kind"`
}

const (
	KindNetwork = "network"
	KindFile    = "file"
	KindLocal   = "local"
)

func kindForHost(host string) string {
	if strings.HasPrefix(host, "file://") {
		return KindFile
	}
	return KindNetwork
}
```

Create `connector/localprinters.go`:

```go
package main

import (
	"regexp"
	"sync"
)

// Queue names reach `lp -d <name>` / winspool as a single exec arg, so shell
// injection is impossible — this allow-list guards against CUPS-invalid and
// just-plain-weird names slipping into job errors and the UI.
var queueNameRE = regexp.MustCompile(`^[A-Za-z0-9_.+-]{1,127}$`)

func validQueueName(name string) bool { return queueNameRE.MatchString(name) }

// LocalPrinters is a concurrency-safe cache of system print queue names,
// refreshed by a ticker in main and read by the heartbeat + job resolution.
type LocalPrinters struct {
	mu    sync.Mutex
	names []string
}

func (l *LocalPrinters) set(names []string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.names = append([]string(nil), names...)
}

func (l *LocalPrinters) Snapshot() []string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]string(nil), l.names...)
}

func (l *LocalPrinters) Has(name string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	for _, n := range l.names {
		if n == name {
			return true
		}
	}
	return false
}

// mergedPrinters is what ReportState and the local API expose: config
// printers (kind computed from host, YAML wins name clashes) + discovered
// system queues as kind=local. Port 9100 on locals only satisfies the
// server schema (1–65535); it is never dialed.
func mergedPrinters(cfg *Config, local []string) []Printer {
	out := make([]Printer, 0, len(cfg.Printers)+len(local))
	seen := make(map[string]bool, len(cfg.Printers))
	for _, p := range cfg.Printers {
		p.Kind = kindForHost(p.Host)
		if p.Port == 0 {
			p.Port = 9100
		}
		out = append(out, p)
		seen[p.Name] = true
	}
	for _, name := range local {
		if seen[name] {
			continue
		}
		out = append(out, Printer{Name: name, Kind: KindLocal, Port: 9100})
	}
	return out
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd connector && go test ./... -v -run 'TestValidQueueName|TestKindForHost|TestLocalPrinters|TestMergedPrinters'`
Expected: 4× PASS. Then the full suite: `go test ./...` — all PASS (existing tests unaffected; `Kind` marshals as `"kind":""` for config printers only until Task 4 wires `mergedPrinters` in — no existing test asserts the JSON of ReportState printers byte-for-byte; if one does fail on the new field, update its expectation in this task).

- [ ] **Step 5: Commit**

```bash
git add connector/config.go connector/localprinters.go connector/localprinters_test.go
git commit -m "feat(connector): printer kinds + local-queue cache and merge (F39)"
```

---

### Task 2: Unix discovery (`lpstat -e`) and printing (`lp -o raw`)

**Files:**
- Create: `connector/localprint_unix.go` (build tag `//go:build !windows`)
- Test: append to `connector/localprinters_test.go`

**Interfaces:**
- Consumes: `validQueueName` (Task 1), `ensureTrailingNewline` (`connector/printer.go:65`), `printTimeout` (`connector/printer.go:13`), `MaxCopies` (`connector/printer.go:16`).
- Produces (used by Tasks 3–4 as the per-platform contract):
  - `func listSystemPrinters() ([]string, error)` — names of OS queues
  - `func printLocal(queue, zpl string, copies int) error`
  - `func (l *LocalPrinters) Refresh()` — added here to `localprinters.go` (portable, calls `listSystemPrinters`)

- [ ] **Step 1: Write the failing tests**

Append to `connector/localprinters_test.go`:

```go
// fakeBin writes an executable shell script into a dir prepended to PATH,
// so listSystemPrinters/printLocal exercise real exec plumbing.
func fakeBin(t *testing.T, dir, name, script string) {
	t.Helper()
	path := filepath.Join(dir, name)
	if err := os.WriteFile(path, []byte("#!/bin/sh\n"+script), 0o755); err != nil {
		t.Fatal(err)
	}
}

func TestListSystemPrinters(t *testing.T) {
	dir := t.TempDir()
	fakeBin(t, dir, "lpstat", `echo "Zebra_ZD421"
echo "bad name with spaces"
echo ""
echo "Office"`)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
	names, err := listSystemPrinters()
	if err != nil {
		t.Fatal(err)
	}
	want := []string{"Zebra_ZD421", "Office"}
	if !reflect.DeepEqual(names, want) {
		t.Fatalf("names = %v, want %v", names, want)
	}
}

func TestLocalPrintersRefresh(t *testing.T) {
	dir := t.TempDir()
	fakeBin(t, dir, "lpstat", `echo "Zebra_ZD421"`)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))
	var l LocalPrinters
	l.Refresh()
	if !l.Has("Zebra_ZD421") {
		t.Fatal("Refresh did not pick up the fake queue")
	}
}

func TestPrintLocal(t *testing.T) {
	dir := t.TempDir()
	argsFile := filepath.Join(dir, "args")
	dataFile := filepath.Join(dir, "data")
	fakeBin(t, dir, "lp", `echo "$@" > `+argsFile+`
cat > `+dataFile)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	if err := printLocal("Zebra_ZD421", "^XA^FDx^FS^XZ", 3); err != nil {
		t.Fatal(err)
	}
	args, _ := os.ReadFile(argsFile)
	wantArgs := "-d Zebra_ZD421 -o raw -n 3 -"
	if strings.TrimSpace(string(args)) != wantArgs {
		t.Errorf("lp args = %q, want %q", strings.TrimSpace(string(args)), wantArgs)
	}
	data, _ := os.ReadFile(dataFile)
	if string(data) != "^XA^FDx^FS^XZ\n" {
		t.Errorf("stdin payload = %q", string(data))
	}
}

func TestPrintLocalErrors(t *testing.T) {
	dir := t.TempDir()
	fakeBin(t, dir, "lp", `echo "lp: The printer or class does not exist." >&2
exit 1`)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	err := printLocal("Ghost", "^XA^XZ", 1)
	if err == nil || !strings.Contains(err.Error(), "does not exist") {
		t.Fatalf("err = %v, want lp stderr in message", err)
	}
	if err := printLocal("bad name", "^XA^XZ", 1); err == nil {
		t.Fatal("invalid queue name must be rejected before exec")
	}
}
```

Add the missing imports to the test file: `os`, `path/filepath`, `reflect`, `strings`.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd connector && go test ./... -run 'TestListSystemPrinters|TestLocalPrintersRefresh|TestPrintLocal' -v`
Expected: compile error — `listSystemPrinters`, `printLocal`, `Refresh` undefined.

- [ ] **Step 3: Implement**

Create `connector/localprint_unix.go`:

```go
//go:build !windows

package main

import (
	"bytes"
	"context"
	"fmt"
	"os/exec"
	"strconv"
	"strings"
)

// listSystemPrinters enumerates CUPS destinations. `lpstat -e` prints one
// queue name per line; names that fail validQueueName are skipped (they
// could not be addressed safely anyway).
func listSystemPrinters() ([]string, error) {
	out, err := exec.Command("lpstat", "-e").Output()
	if err != nil {
		return nil, fmt.Errorf("lpstat -e: %w", err)
	}
	var names []string
	for _, line := range strings.Split(string(out), "\n") {
		name := strings.TrimSpace(line)
		if name != "" && validQueueName(name) {
			names = append(names, name)
		}
	}
	return names, nil
}

// printLocal sends raw bytes to a CUPS queue. `-o raw` bypasses filters,
// `-n` does copies natively, `-` reads the payload from stdin. No shell.
func printLocal(queue, zpl string, copies int) error {
	if !validQueueName(queue) {
		return fmt.Errorf("printer %q: invalid queue name", queue)
	}
	ctx, cancel := context.WithTimeout(context.Background(), printTimeout)
	defer cancel()
	cmd := exec.CommandContext(ctx, "lp", "-d", queue, "-o", "raw",
		"-n", strconv.Itoa(copies), "-")
	cmd.Stdin = strings.NewReader(ensureTrailingNewline(zpl))
	var stderr bytes.Buffer
	cmd.Stderr = &stderr
	if err := cmd.Run(); err != nil {
		msg := strings.TrimSpace(stderr.String())
		if msg == "" {
			msg = err.Error()
		}
		if len(msg) > 500 {
			msg = msg[:500]
		}
		return fmt.Errorf("printer %s (local queue): %s", queue, msg)
	}
	return nil
}
```

Append to `connector/localprinters.go` (portable — both platforms provide `listSystemPrinters`):

```go
// Refresh re-reads the system queues. Errors (no CUPS, no lpstat) leave the
// previous snapshot untouched — a discovery hiccup must not unlist printers
// that jobs may be in flight for; a missing subsystem simply yields nothing.
func (l *LocalPrinters) Refresh() {
	names, err := listSystemPrinters()
	if err != nil {
		return
	}
	l.set(names)
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd connector && go test ./... -v`
Expected: all PASS, including the five new tests.

- [ ] **Step 5: Commit**

```bash
git add connector/localprint_unix.go connector/localprinters.go connector/localprinters_test.go
git commit -m "feat(connector): CUPS discovery (lpstat -e) + raw printing via lp (F39)"
```

---

### Task 3: Windows implementation (winspool, no cgo)

**Files:**
- Create: `connector/localprint_windows.go` (build tag `//go:build windows`)
- Modify: `connector/go.mod` / `go.sum` (new dependency)

**Interfaces:**
- Consumes: `validQueueName`, `ensureTrailingNewline`, `MaxCopies` (same contract as Task 2).
- Produces: the same two functions as Task 2, for GOOS=windows: `listSystemPrinters() ([]string, error)`, `printLocal(queue, zpl string, copies int) error`.

- [ ] **Step 1: Add the dependency**

```bash
cd connector && go get github.com/alexbrainman/printer@latest
```

Expected: `go.mod` gains `require github.com/alexbrainman/printer v0.0.0-…` — syscall-only, **no cgo**.

- [ ] **Step 2: Implement**

Create `connector/localprint_windows.go`:

```go
//go:build windows

package main

import (
	"fmt"
	"strings"

	winprinter "github.com/alexbrainman/printer"
)

// listSystemPrinters enumerates installed Windows printers via winspool
// (EnumPrinters under the hood — pure syscalls, no cgo).
func listSystemPrinters() ([]string, error) {
	all, err := winprinter.ReadNames()
	if err != nil {
		return nil, fmt.Errorf("EnumPrinters: %w", err)
	}
	var names []string
	for _, n := range all {
		if validQueueName(n) {
			names = append(names, n)
		}
	}
	return names, nil
}

// printLocal spools one RAW document to a local Windows printer. Copies are
// realized by repeating the payload inside a single document (mirrors the
// TCP path — RAW has no native copies count).
func printLocal(queue, zpl string, copies int) error {
	if !validQueueName(queue) {
		return fmt.Errorf("printer %q: invalid queue name", queue)
	}
	p, err := winprinter.Open(queue)
	if err != nil {
		return fmt.Errorf("printer %s (local queue): %w", queue, err)
	}
	defer p.Close()
	if err := p.StartRawDocument("BarcodeLabelGen label"); err != nil {
		return fmt.Errorf("printer %s (local queue): %w", queue, err)
	}
	defer p.EndDocument()
	payload := strings.Repeat(ensureTrailingNewline(zpl), copies)
	if _, err := p.Write([]byte(payload)); err != nil {
		return fmt.Errorf("printer %s (local queue): write: %w", queue, err)
	}
	return nil
}
```

Note: Windows names may contain spaces (`"ZDesigner ZD421"`) which `validQueueName` rejects. **Loosen the check for Windows names is wrong** — instead relax the shared regex in `connector/localprinters.go` to allow inner spaces, since neither `lp` args nor winspool interpret them:

```go
var queueNameRE = regexp.MustCompile(`^[A-Za-z0-9_.+-]([A-Za-z0-9_.+ -]{0,125}[A-Za-z0-9_.+-])?$`)
```

Also update `TestValidQueueName` in `connector/localprinters_test.go`: move `"has space"` from the invalid list to the valid list (inner spaces OK) and add `" leading"` and `"trailing "` to the invalid list. CUPS itself never emits names with spaces, so the unix path is unaffected.

- [ ] **Step 3: Verify both platforms compile and unix tests still pass**

```bash
cd connector && go vet ./... && go test ./... \
  && GOOS=windows GOARCH=amd64 CGO_ENABLED=0 go build -o /dev/null . \
  && ./build-all.sh
```

Expected: tests PASS; the Windows build and all six `build-all.sh` targets succeed (zero-cgo matrix intact).

- [ ] **Step 4: Commit**

```bash
git add connector/go.mod connector/go.sum connector/localprint_windows.go \
  connector/localprinters.go connector/localprinters_test.go
git commit -m "feat(connector): Windows local printing via winspool RAW (F39)"
```

---

### Task 4: Wiring — `Print()` dispatch, main loop ticker, job resolution, local API

**Files:**
- Modify: `connector/printer.go:22-32` (dispatch)
- Modify: `connector/main.go` (ticker + merged report + job fallback; log line)
- Modify: `connector/localapi.go` (constructor + `/printers` + `/print` see local queues)
- Test: append to `connector/localprinters_test.go`

**Interfaces:**
- Consumes: `LocalPrinters`, `mergedPrinters`, `printLocal`, `KindLocal` (Tasks 1–3); `Client.ReportState(version string, printers []Printer)` (`connector/client.go:85`); `NewLocalAPI(cfg *Config)` (`connector/localapi.go`).
- Produces:
  - `Print(p Printer, zpl string, copies int) error` handles `p.Kind == KindLocal`
  - `func resolvePrinter(cfg *Config, local *LocalPrinters, name string) (Printer, bool)`
  - `NewLocalAPI(cfg *Config, local *LocalPrinters) *LocalAPI` — **signature change**; update all call sites (`main.go`, `connector_test.go`).

- [ ] **Step 1: Write the failing tests**

Append to `connector/localprinters_test.go`:

```go
func TestPrintDispatchesLocal(t *testing.T) {
	dir := t.TempDir()
	dataFile := filepath.Join(dir, "data")
	fakeBin(t, dir, "lp", `cat > `+dataFile)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	err := Print(Printer{Name: "Zebra_ZD421", Kind: KindLocal}, "^XA^XZ", 1)
	if err != nil {
		t.Fatal(err)
	}
	if data, _ := os.ReadFile(dataFile); string(data) != "^XA^XZ\n" {
		t.Fatalf("payload = %q", string(data))
	}
}

func TestResolvePrinter(t *testing.T) {
	cfg := &Config{Printers: []Printer{{Name: "drukarka", Host: "10.0.0.5", Port: 9100}}}
	var local LocalPrinters
	local.set([]string{"Zebra_ZD421"})

	p, ok := resolvePrinter(cfg, &local, "drukarka")
	if !ok || p.Host != "10.0.0.5" {
		t.Fatalf("config printer not resolved: %+v ok=%v", p, ok)
	}
	p, ok = resolvePrinter(cfg, &local, "Zebra_ZD421")
	if !ok || p.Kind != KindLocal {
		t.Fatalf("local printer not resolved: %+v ok=%v", p, ok)
	}
	if _, ok := resolvePrinter(cfg, &local, "Ghost"); ok {
		t.Fatal("unknown printer must not resolve")
	}
}
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd connector && go test ./... -run 'TestPrintDispatchesLocal|TestResolvePrinter' -v`
Expected: compile error — `resolvePrinter` undefined; `TestPrintDispatchesLocal` fails (local kind falls through to TCP dial).

- [ ] **Step 3: Implement**

`connector/printer.go` — dispatch on kind first:

```go
func Print(p Printer, zpl string, copies int) error {
	if copies < 1 {
		copies = 1
	}
	if copies > MaxCopies {
		copies = MaxCopies
	}
	if p.Kind == KindLocal {
		return printLocal(p.Name, zpl, copies)
	}
	if p.IsFile() {
		return printToFile(p, zpl, copies)
	}
	return printToTCP(p, zpl, copies)
}
```

`connector/localprinters.go` — add resolution used by the poll loop and local API:

```go
// resolvePrinter finds a job's target: config printers win, then any
// currently-discovered system queue prints as kind=local.
func resolvePrinter(cfg *Config, local *LocalPrinters, name string) (Printer, bool) {
	if p, ok := cfg.PrinterByName(name); ok {
		p.Kind = kindForHost(p.Host)
		return p, true
	}
	if local.Has(name) {
		return Printer{Name: name, Kind: KindLocal, Port: 9100}, true
	}
	return Printer{}, false
}
```

`connector/main.go`:
1. Create the cache near startup and refresh once before the first heartbeat, then start the ticker goroutine:

```go
	local := &LocalPrinters{}
	local.Refresh()
	go func() {
		t := time.NewTicker(60 * time.Second)
		defer t.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-t.C:
				local.Refresh()
			}
		}
	}()
```

2. Replace the heartbeat's copy-and-default block (`main.go:76-82`) with:

```go
		if err := client.ReportState(Version, mergedPrinters(cfg, local.Snapshot())); err != nil {
```

3. Replace the job resolution (`main.go:96-99`) with:

```go
			printer, ok := resolvePrinter(cfg, local, job.Printer)
			if !ok {
				log.Printf("job %d: unknown printer %q", job.ID, job.Printer)
				_ = client.ReportStatus(job.ID, "error", fmt.Sprintf("printer %q not available on this device", job.Printer))
				continue
			}
```

4. Extend the startup log (`main.go:114`) to include discovered count:

```go
	log.Printf("blg-connector %s → %s (%d printers, %d local queues, poll %s)",
		Version, cfg.ServerURL, len(cfg.Printers), len(local.Snapshot()), cfg.PollInterval())
```

(Adjust ordering so `local` exists before the log line; keep the ctx used by the ticker consistent with the existing shutdown context in main.)

`connector/localapi.go`:
1. `NewLocalAPI(cfg *Config, local *LocalPrinters) *LocalAPI` — store `local *LocalPrinters` in the struct.
2. `/printers` handler returns the merged view: `writeJSON(w, http.StatusOK, map[string]any{"printers": mergedPrinters(a.cfg, a.local.Snapshot())})`.
3. `/print` handler resolves via `resolvePrinter(a.cfg, a.local, req.Printer)` instead of `cfg.PrinterByName`.
4. Update every call site: `main.go` and each `NewLocalAPI(` occurrence in `connector/connector_test.go` (pass `&LocalPrinters{}`).

- [ ] **Step 4: Run the full connector suite + builds**

```bash
cd connector && go vet ./... && go test ./... && ./build-all.sh
```

Expected: all PASS, six binaries built.

- [ ] **Step 5: Commit**

```bash
git add connector/printer.go connector/main.go connector/localapi.go \
  connector/localprinters.go connector/localprinters_test.go connector/connector_test.go
git commit -m "feat(connector): wire local queues into heartbeat, jobs and local API (F39)"
```

---

### Task 5: Backend — `kind` in the agent printers schema

**Files:**
- Modify: `backend/app/schemas/device.py:65-73` (`AgentPrinter`)
- Test: `backend/tests/test_agent_endpoints.py` (extend existing + new)

**Interfaces:**
- Consumes: `AgentPrinter`, `AgentStateRequest` (existing), `/api/agent/state` route (`backend/app/routes/agent.py:95`, no route change needed — it dumps the schema).
- Produces: stored `device.printers` entries shaped `{"name", "host", "port", "kind"}` — consumed by the frontend (Task 6).

- [ ] **Step 1: Write the failing tests**

In `backend/tests/test_agent_endpoints.py`, update `test_agent_state_updates_device` — the stored dict now includes the defaulted kind:

```python
    assert device["printers"] == [
        {"name": "Zebra-1", "host": "192.168.1.50", "port": 9100, "kind": "network"}
    ]
```

Add below it:

```python
def test_agent_state_accepts_local_printers(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    """F39: discovered system queues report kind=local and no host."""
    _device_id, token = _setup(app, client, csrf)
    resp = client.post(
        "/api/agent/state",
        json={
            "agent_version": "0.6.0",
            "printers": [
                {"name": "drukarka", "host": "192.168.1.50", "port": 9100, "kind": "network"},
                {"name": "Zebra_ZD421", "host": "", "port": 9100, "kind": "local"},
            ],
        },
        headers=_bearer(token),
    )
    assert resp.status_code == 200
    printers = client.get("/api/devices").get_json()["devices"][0]["printers"]
    assert printers[1] == {"name": "Zebra_ZD421", "host": "", "port": 9100, "kind": "local"}


def test_agent_state_rejects_remote_printer_without_host(
    app: Flask, client: FlaskClient, csrf: CsrfHelper
) -> None:
    _device_id, token = _setup(app, client, csrf)
    resp = client.post(
        "/api/agent/state",
        json={"printers": [{"name": "x", "host": "", "port": 9100, "kind": "network"}]},
        headers=_bearer(token),
    )
    assert resp.status_code == 400
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd backend && uv run pytest tests/test_agent_endpoints.py -q`
Expected: 3 failures — `kind` unexpected/absent, empty host rejected by `min_length=1`.

- [ ] **Step 3: Implement**

In `backend/app/schemas/device.py` replace `AgentPrinter`:

```python
class AgentPrinter(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    # Empty host is legal only for kind="local" (a queue discovered on the
    # connector's computer) — see the validator below.
    host: str = Field(default="", max_length=255)
    port: int = Field(default=9100, ge=1, le=65535)
    kind: Literal["network", "file", "local"] = "network"

    @model_validator(mode="after")
    def _host_required_unless_local(self) -> "AgentPrinter":
        if self.kind != "local" and not self.host:
            raise ValueError("host is required for network/file printers")
        return self
```

Add `model_validator` to the existing pydantic import in that file (and `Literal` to typing imports if missing).

- [ ] **Step 4: Run the backend suite**

Run: `cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q`
Expected: all green.

- [ ] **Step 5: Commit**

```bash
git add backend/app/schemas/device.py backend/tests/test_agent_endpoints.py
git commit -m "feat(devices): accept kind=local printers from agents (F39)"
```

---

### Task 6: Frontend — badge local printers in PrintModal and DevicesPage

**Files:**
- Modify: `frontend/src/lib/types.ts:19-23` (`DevicePrinter`)
- Modify: `frontend/src/editor/PrintModal.tsx:196-198` and the printer `<Select>` options (~line 256)
- Modify: `frontend/src/pages/DevicesPage.tsx:96`
- Modify: `frontend/src/i18n/locales/pl.json`, `frontend/src/i18n/locales/en.json`

**Interfaces:**
- Consumes: `device.printers[].kind` from the API (Task 5).
- Produces: UI only — no new exports.

- [ ] **Step 1: Extend the type**

In `frontend/src/lib/types.ts`:

```ts
export type DevicePrinter = {
  name: string;
  host: string;
  port: number;
  /** F39: "local" = a queue discovered on the connector's computer. */
  kind?: "network" | "file" | "local";
};
```

- [ ] **Step 2: i18n keys**

`pl.json` (inside the existing `"print"` object): `"localPrinter": "drukarka z tego komputera"`.
`pl.json` (inside `"devices"`): `"localPrinter": "lokalna"`.
`en.json`: `"localPrinter": "printer on this computer"` (print) and `"localPrinter": "local"` (devices).

- [ ] **Step 3: PrintModal**

Keep `kind` when mapping the local-agent list (line ~196-198):

```ts
  const reportedPrinters =
    deviceId === LOCAL
      ? (localPrinters.data?.map((p) => ({ name: p.name, host: p.host, kind: p.kind })) ?? [])
      : (selectedDevice?.printers ?? []);
```

In the printer `<Select>` options (directly under `label={t("print.printer")}` at ~line 257), render the badge in the option text:

```tsx
{reportedPrinters.map((p) => (
  <option key={p.name} value={p.name}>
    {p.name}
    {p.kind === "local" ? ` — ${t("print.localPrinter")}` : ""}
  </option>
))}
```

(Adapt to the exact existing option markup — only append the conditional suffix; do not restructure the Select.)

- [ ] **Step 4: DevicesPage**

Line ~96, append the badge in the joined list:

```tsx
{d.printers.length === 0
  ? "—"
  : d.printers
      .map((p) => (p.kind === "local" ? `${p.name} (${t("devices.localPrinter")})` : p.name))
      .join(", ")}
```

- [ ] **Step 5: Verify**

Run: `cd frontend && npm run format:check && npm run lint && npm run typecheck && npm run build`
(If Prettier complains, run `npx prettier --write` on the touched files first.)
Expected: all green.

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/types.ts frontend/src/editor/PrintModal.tsx \
  frontend/src/pages/DevicesPage.tsx frontend/src/i18n/locales/pl.json frontend/src/i18n/locales/en.json
git commit -m "feat(devices): show local (USB/system) printers with a badge (F39)"
```

---

### Task 7: Docs, changelog, release v0.22.0

**Files:**
- Modify: `connector/README.md` (new section „Drukarki lokalne (USB)")
- Modify: `connector/version.go` (`Version = "0.6.0"`)
- Modify: `CHANGELOG.md`, `backend/app/version.py`, `backend/pyproject.toml`, `frontend/package.json` (+ `backend/uv.lock` via `uv lock`)

**Interfaces:** none — release mechanics.

- [ ] **Step 1: connector README section**

Add after the existing printers section (adapt placement to the file's flow), in Polish like the rest of the file:

```markdown
## Drukarki lokalne (USB) — zero konfiguracji

Agent co 60 s wykrywa systemowe kolejki druku (macOS/Linux: CUPS przez
`lpstat -e`; Windows: zainstalowane drukarki przez winspool) i zgłasza je
serwerowi obok drukarek z `config.yaml`. Drukarka podłączona po USB
(np. Zebra ZD421) wystarczy, że jest dodana w ustawieniach systemu —
w BLG pojawi się automatycznie jako „drukarka z tego komputera".

- Druk: macOS/Linux `lp -d <kolejka> -o raw -n <kopie>`; Windows RAW przez
  winspool. Sterowniki i filtry systemowe są omijane (raw).
- Przy konflikcie nazw z `config.yaml` wygrywa konfiguracja YAML.
- Brak CUPS/`lpstat` = po prostu brak wykrytych drukarek (bez błędu).
```

- [ ] **Step 2: version bumps + changelog**

- `connector/version.go`: `const Version = "0.6.0"`.
- `backend/app/version.py`: `APP_VERSION = "0.22.0"`; `backend/pyproject.toml`: `version = "0.22.0"`; `frontend/package.json`: `"version": "0.22.0"`; then `cd backend && uv lock`.
- `CHANGELOG.md`: new `## [0.22.0] — <date>` section under `[Unreleased]` with `### Added` describing F39 (discovery, local RAW printing, kind badge, no migration), and update the link refs at the bottom (`[Unreleased]` compare base → v0.22.0, add `[0.22.0]` tag link).

- [ ] **Step 3: Full verification**

```bash
cd connector && go vet ./... && go test ./... && ./build-all.sh
cd ../backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
cd ../frontend && npm run format:check && npm run lint && npm run typecheck && npm run build
```

Expected: everything green (including `tests/test_version_sync.py`).

- [ ] **Step 4: Commit, tag, release**

```bash
git add -A && git commit -m "chore(release): v0.22.0 — local (USB/system) printers via connector (F39)"
git tag -a v0.22.0 -m "v0.22.0 — local (USB/system) printers via connector (F39)"
git push origin main && git push origin v0.22.0
gh release create v0.22.0 --title "v0.22.0 — local (USB/system) printers (F39)" \
  --notes "<CHANGELOG 0.22.0 section>"
```

The `release.yml` workflow attaches the six connector binaries + `SHA256SUMS` automatically — verify with `gh release view v0.22.0 --json assets`.

- [ ] **Step 5: Manual E2E (user hardware)**

On the user's Mac: install/replace the connector binary (v0.6.0), confirm the ZD421 CUPS queue exists (`lpstat -e`), watch the Devices page list „Zebra_ZD421 (lokalna)", print a label from the editor queue and from the browser fast path. This step is a user-assisted checkpoint — report results before closing F39.
