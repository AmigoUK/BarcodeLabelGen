# F36 — Android Connector (Go core + Kotlin shell plan) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a gomobile-friendly Go core (`connector/mobilecore/`) that polls the BarcodeLabelGen job queue and prints ZPL over RAW TCP 9100, fully unit-tested in this repo, plus documentation for the Kotlin/Android shell and gomobile AAR build (which are built and verified on a machine with the Android toolchain — none exists here).

**Architecture:** A standalone Go package `connector/mobilecore` (subpackage of the existing `connector` module, non-`main` so gomobile can bind it) exposes a string-in/string-out API — `NewAgent`, `RunOnce` (returns a JSON summary), `ReportState` — mirroring the proven desktop agent↔server contract. The desktop agent is left untouched. The Kotlin shell (foreground `PrintService` + `MainActivity`) calls the AAR built via `gomobile bind`; it is documented, not built here.

**Tech Stack:** Go 1.22 (core + tests, verifiable here); gomobile bind → AAR, Kotlin/Jetpack, Android SDK (shell — documented, off-device).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-04-f36-android-connector-design.md`.
- Module path: `github.com/AmigoUK/BarcodeLabelGen/connector`; package is `github.com/AmigoUK/BarcodeLabelGen/connector/mobilecore`.
- **Desktop connector (`connector/*.go` in package main) MUST NOT be modified.** `mobilecore` is standalone; the small logic duplication is intentional.
- gomobile bind constraints: exported funcs use only `string`, `int`, `bool`, `[]byte`, and pointers to package structs/interfaces. **No `[]Job` across the boundary** — `RunOnce` returns a JSON string.
- Agent↔server contract (verbatim from spec): `GET /api/agent/jobs` with `Authorization: Bearer <token>` → `{"jobs":[{"id":int,"printer":string,"copies":int,"zpl":string}]}`; print = TCP dial `host:port`, write `ensureTrailingNewline(zpl)` repeated `copies` times (clamp 1..1000), 10s timeout; `POST /api/agent/jobs/{id}/status` → `{"status":"done"|"error","error":?}`; `POST /api/agent/state` → `{"agent_version":string,"printers":[{"name","host","port"}]}`; 401 → auth error.
- Job-to-printer match mirrors desktop: a job whose `printer` != the configured printer name is reported `error` ("printer %q not configured on this device"), not printed.
- HTTP client timeout 15s; print timeout 10s.
- Tests: table-driven where natural; use `net/http/httptest` for the server and a `net.Listener` for the printer. Run `gofmt -l .`, `go vet ./...`, `go test ./mobilecore/...` — all clean.
- Version bump: app `0.18.0 → 0.19.0` (`frontend/package.json`, `backend/pyproject.toml`) for adding the mobile core. Connector `version.go` stays `0.5.0` (desktop binary unchanged). Android module has its own `versionName` starting `0.1.0` (documented, not built).
- Commit messages end with `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `mobilecore` — ZPL check + TCP print (pure, testable)

**Files:**
- Create: `connector/mobilecore/zpl.go`
- Create: `connector/mobilecore/print.go`
- Test: `connector/mobilecore/print_test.go`, `connector/mobilecore/zpl_test.go`

**Interfaces:**
- Consumes: nothing.
- Produces: `func looksLikeZPL(data []byte) (bool, string)`; `func ensureTrailingNewline(s string) string`; `func printTCP(host string, port int, zpl string, copies int) error` (clamps copies to 1..1000). Task 3 calls these.

- [ ] **Step 1: Write `zpl.go`**

```go
package mobilecore

import "strings"

// looksLikeZPL mirrors the desktop agent's zplcheck.go and the server's F29
// gate: a cheap sanity check before printing. Returns ok=false with a short
// reason for non-ZPL payloads.
func looksLikeZPL(data []byte) (bool, string) {
	s := strings.TrimSpace(string(data))
	if s == "" {
		return false, "payload is empty"
	}
	head := strings.ToLower(s[:min(len(s), 64)])
	for prefix, name := range map[string]string{
		"<!doctype": "HTML document",
		"<html":     "HTML document",
		"%pdf-":     "PDF document",
		"%!ps":      "PostScript document",
		"\x1b%":     "PCL print stream",
		"\x1be":     "PCL print stream",
		"{":         "JSON document",
	} {
		if strings.HasPrefix(head, prefix) {
			return false, "payload looks like a " + name + ", not ZPL"
		}
	}
	start := strings.Index(s, "^XA")
	end := strings.LastIndex(s, "^XZ")
	switch {
	case start == -1:
		return false, "payload contains no ^XA label start"
	case end == -1:
		return false, "payload contains no ^XZ label end"
	case end < start:
		return false, "last ^XZ appears before first ^XA"
	}
	return true, ""
}

// ensureTrailingNewline guarantees the printer sees a job terminator.
func ensureTrailingNewline(s string) string {
	if strings.HasSuffix(s, "\n") {
		return s
	}
	return s + "\n"
}
```

- [ ] **Step 2: Write `print.go`**

```go
package mobilecore

import (
	"fmt"
	"net"
	"strings"
	"time"
)

const (
	printTimeout = 10 * time.Second
	maxCopies    = 1000 // mirrors the server-side schema limit
)

// printTCP sends the ZPL to host:port `copies` times over one RAW TCP
// (JetDirect / 9100) connection, with the payload repeated.
func printTCP(host string, port int, zpl string, copies int) error {
	if copies < 1 {
		copies = 1
	}
	if copies > maxCopies {
		copies = maxCopies
	}
	addr := net.JoinHostPort(host, fmt.Sprintf("%d", port))
	conn, err := net.DialTimeout("tcp", addr, printTimeout)
	if err != nil {
		return fmt.Errorf("printer %s: %w", addr, err)
	}
	defer conn.Close()
	_ = conn.SetWriteDeadline(time.Now().Add(printTimeout))
	payload := strings.Repeat(ensureTrailingNewline(zpl), copies)
	if _, err := conn.Write([]byte(payload)); err != nil {
		return fmt.Errorf("printer %s: write: %w", addr, err)
	}
	return nil
}
```

- [ ] **Step 3: Write `zpl_test.go`**

```go
package mobilecore

import "testing"

func TestLooksLikeZPL(t *testing.T) {
	cases := []struct {
		name string
		in   string
		ok   bool
	}{
		{"valid", "^XA^FO10,10^FDhi^FS^XZ", true},
		{"valid with whitespace", "  \n^XA^XZ\n ", true},
		{"empty", "   ", false},
		{"postscript", "%!PS-Adobe-3.0\nshowpage", false},
		{"pdf", "%PDF-1.7 ...", false},
		{"html", "<!DOCTYPE html><html>", false},
		{"no XA", "^FO10,10^FDhi^FS^XZ", false},
		{"no XZ", "^XA^FO10,10", false},
		{"XZ before XA", "^XZ junk ^XA", false},
	}
	for _, c := range cases {
		t.Run(c.name, func(t *testing.T) {
			ok, reason := looksLikeZPL([]byte(c.in))
			if ok != c.ok {
				t.Fatalf("looksLikeZPL(%q) ok=%v reason=%q, want ok=%v", c.in, ok, reason, c.ok)
			}
		})
	}
}

func TestEnsureTrailingNewline(t *testing.T) {
	if got := ensureTrailingNewline("^XZ"); got != "^XZ\n" {
		t.Fatalf("got %q", got)
	}
	if got := ensureTrailingNewline("^XZ\n"); got != "^XZ\n" {
		t.Fatalf("got %q", got)
	}
}
```

- [ ] **Step 4: Write `print_test.go`** (captures bytes on a local listener)

```go
package mobilecore

import (
	"io"
	"net"
	"strings"
	"testing"
)

// acceptOne starts a listener, returns its host, port, and a channel that
// receives the bytes of the single connection it accepts.
func acceptOne(t *testing.T) (string, int, <-chan []byte) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	got := make(chan []byte, 1)
	go func() {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer ln.Close()
		defer conn.Close()
		b, _ := io.ReadAll(conn)
		got <- b
	}()
	host, portStr, _ := net.SplitHostPort(ln.Addr().String())
	port := ln.Addr().(*net.TCPAddr).Port
	_ = portStr
	return host, port, got
}

func TestPrintTCPRepeatsWithNewline(t *testing.T) {
	host, port, got := acceptOne(t)
	if err := printTCP(host, port, "^XA^XZ", 3); err != nil {
		t.Fatal(err)
	}
	b := <-got
	if want := strings.Repeat("^XA^XZ\n", 3); string(b) != want {
		t.Fatalf("got %q want %q", b, want)
	}
}

func TestPrintTCPClampsCopies(t *testing.T) {
	host, port, got := acceptOne(t)
	if err := printTCP(host, port, "^XA^XZ", 0); err != nil { // 0 -> 1
		t.Fatal(err)
	}
	b := <-got
	if want := "^XA^XZ\n"; string(b) != want {
		t.Fatalf("copies=0 got %q want one copy %q", b, want)
	}
}

func TestPrintTCPUnreachable(t *testing.T) {
	// Port 1 on loopback refuses quickly.
	if err := printTCP("127.0.0.1", 1, "^XA^XZ", 1); err == nil {
		t.Fatal("expected error dialing unreachable printer")
	}
}
```

- [ ] **Step 5: Run the tests**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
go test ./mobilecore/... -run 'ZPL|Newline|PrintTCP' -v
```
Expected: all PASS.

- [ ] **Step 6: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/mobilecore/zpl.go connector/mobilecore/print.go connector/mobilecore/zpl_test.go connector/mobilecore/print_test.go
git commit -m "feat(mobilecore): ZPL check + TCP print core for Android (F36)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `mobilecore` — Agent HTTP client (poll / status / state)

**Files:**
- Create: `connector/mobilecore/agent.go`
- Test: `connector/mobilecore/agent_test.go`

**Interfaces:**
- Consumes: nothing from Task 1 (independent).
- Produces:
  - `type Agent struct{…}`; `func NewAgent(serverURL, token, agentVersion string) *Agent`
  - internal `type job struct{ ID int; Printer string; Copies int; Zpl string }` (json tags `id/printer/copies/zpl`)
  - internal `func (a *Agent) pollJobs() ([]job, error)` (returns `errUnauthorized` sentinel on 401)
  - internal `func (a *Agent) reportStatus(id int, status, errMsg string) error`
  - internal `func (a *Agent) reportState(name, host string, port int) error`
  - exported `func (a *Agent) ReportState(printerName, printerHost string, printerPort int) error`
  - package var `errUnauthorized error`
  Task 3 calls `pollJobs`, `reportStatus`, and reuses `Agent`/`errUnauthorized`.

- [ ] **Step 1: Write `agent.go`**

```go
package mobilecore

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
)

// errUnauthorized is returned when the server rejects the device token (401),
// so RunOnce can surface authError to the Kotlin shell.
var errUnauthorized = errors.New("device token rejected (401)")

// Agent talks to the BarcodeLabelGen agent API with a device token. It is the
// gomobile-bound entry point; construct it with NewAgent.
type Agent struct {
	serverURL    string
	token        string
	agentVersion string
	http         *http.Client
}

// NewAgent creates an Agent. gomobile binds this as a constructor.
func NewAgent(serverURL, token, agentVersion string) *Agent {
	return &Agent{
		serverURL:    serverURL,
		token:        token,
		agentVersion: agentVersion,
		http:         &http.Client{Timeout: 15 * time.Second},
	}
}

type job struct {
	ID      int    `json:"id"`
	Printer string `json:"printer"`
	Copies  int    `json:"copies"`
	Zpl     string `json:"zpl"`
}

func (a *Agent) do(method, path string, body any, out any) error {
	var reader io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return err
		}
		reader = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, a.serverURL+path, reader)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+a.token)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := a.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusUnauthorized {
		return errUnauthorized
	}
	if resp.StatusCode >= 400 {
		snippet, _ := io.ReadAll(io.LimitReader(resp.Body, 500))
		return fmt.Errorf("%s %s: HTTP %d: %s", method, path, resp.StatusCode, snippet)
	}
	if out != nil {
		return json.NewDecoder(resp.Body).Decode(out)
	}
	return nil
}

func (a *Agent) pollJobs() ([]job, error) {
	var payload struct {
		Jobs []job `json:"jobs"`
	}
	if err := a.do(http.MethodGet, "/api/agent/jobs", nil, &payload); err != nil {
		return nil, err
	}
	return payload.Jobs, nil
}

func (a *Agent) reportStatus(id int, status, errMsg string) error {
	body := map[string]any{"status": status}
	if errMsg != "" {
		body["error"] = errMsg
	}
	return a.do(http.MethodPost, fmt.Sprintf("/api/agent/jobs/%d/status", id), body, nil)
}

func (a *Agent) reportState(name, host string, port int) error {
	body := map[string]any{
		"agent_version": a.agentVersion,
		"printers":      []map[string]any{{"name": name, "host": host, "port": port}},
	}
	return a.do(http.MethodPost, "/api/agent/state", body, nil)
}

// ReportState sends a heartbeat with the single configured printer. gomobile
// binds this; the Kotlin shell calls it periodically.
func (a *Agent) ReportState(printerName, printerHost string, printerPort int) error {
	return a.reportState(printerName, printerHost, printerPort)
}
```

- [ ] **Step 2: Write `agent_test.go`**

```go
package mobilecore

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPollJobsParsesAndSendsBearer(t *testing.T) {
	var gotAuth string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		if r.Method != http.MethodGet || r.URL.Path != "/api/agent/jobs" {
			t.Errorf("unexpected %s %s", r.Method, r.URL.Path)
		}
		io.WriteString(w, `{"jobs":[{"id":7,"printer":"Zebra-1","copies":2,"zpl":"^XA^XZ"}]}`)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "blg_tok", "0.1.0")
	jobs, err := a.pollJobs()
	if err != nil {
		t.Fatal(err)
	}
	if gotAuth != "Bearer blg_tok" {
		t.Fatalf("auth header = %q", gotAuth)
	}
	if len(jobs) != 1 || jobs[0].ID != 7 || jobs[0].Copies != 2 || jobs[0].Printer != "Zebra-1" {
		t.Fatalf("jobs = %+v", jobs)
	}
}

func TestPollJobs401(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "bad", "0.1.0")
	_, err := a.pollJobs()
	if !errors.Is(err, errUnauthorized) {
		t.Fatalf("want errUnauthorized, got %v", err)
	}
}

func TestReportStatusBody(t *testing.T) {
	var body map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agent/jobs/7/status" {
			t.Errorf("path %s", r.URL.Path)
		}
		json.NewDecoder(r.Body).Decode(&body)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.1.0")
	if err := a.reportStatus(7, "error", "boom"); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "error" || body["error"] != "boom" {
		t.Fatalf("body = %+v", body)
	}
}

func TestReportStateBody(t *testing.T) {
	var body map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agent/state" {
			t.Errorf("path %s", r.URL.Path)
		}
		json.NewDecoder(r.Body).Decode(&body)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.9.9")
	if err := a.ReportState("Zebra-1", "192.168.1.50", 9100); err != nil {
		t.Fatal(err)
	}
	if body["agent_version"] != "0.9.9" {
		t.Fatalf("agent_version = %v", body["agent_version"])
	}
	printers, ok := body["printers"].([]any)
	if !ok || len(printers) != 1 {
		t.Fatalf("printers = %v", body["printers"])
	}
	p := printers[0].(map[string]any)
	if p["name"] != "Zebra-1" || p["host"] != "192.168.1.50" || p["port"].(float64) != 9100 {
		t.Fatalf("printer = %+v", p)
	}
}
```

- [ ] **Step 3: Run the tests**

Run:
```bash
cd /var/www/html/BarcodeLabelGen
go test ./connector/mobilecore/... -run 'PollJobs|ReportStatus|ReportState' -v
```
Expected: all PASS.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/mobilecore/agent.go connector/mobilecore/agent_test.go
git commit -m "feat(mobilecore): device-token agent client (poll/status/state) (F36)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: `mobilecore` — RunOnce orchestration + JSON summary

**Files:**
- Create: `connector/mobilecore/runonce.go`
- Test: `connector/mobilecore/runonce_test.go`

**Interfaces:**
- Consumes: `looksLikeZPL`, `printTCP` (Task 1); `Agent`, `pollJobs`, `reportStatus`, `errUnauthorized` (Task 2).
- Produces: exported `func (a *Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error)` returning JSON `{"polled":int,"printed":int,"failed":int,"messages":[string],"authError":bool}`.

- [ ] **Step 1: Write `runonce.go`**

```go
package mobilecore

import (
	"encoding/json"
	"errors"
	"fmt"
)

type runSummary struct {
	Polled    int      `json:"polled"`
	Printed   int      `json:"printed"`
	Failed    int      `json:"failed"`
	Messages  []string `json:"messages"`
	AuthError bool     `json:"authError"`
}

func (s runSummary) json() string {
	// Messages must never marshal to null (Kotlin expects an array).
	if s.Messages == nil {
		s.Messages = []string{}
	}
	out, _ := json.Marshal(s)
	return string(out)
}

// RunOnce performs one poll → print → report cycle and returns a JSON summary.
// A job whose printer name != printerName is rejected (mirrors the desktop
// agent). The returned error is non-nil only for a whole-cycle failure (e.g.
// the poll itself failed); per-job failures are counted in Failed/Messages and
// reported to the server. On a 401 the summary's authError is true.
func (a *Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error) {
	jobs, err := a.pollJobs()
	if err != nil {
		s := runSummary{AuthError: errors.Is(err, errUnauthorized)}
		return s.json(), err
	}
	s := runSummary{Polled: len(jobs)}
	for _, j := range jobs {
		if j.Printer != printerName {
			msg := fmt.Sprintf("job %d: printer %q not configured on this device", j.ID, j.Printer)
			s.Failed++
			s.Messages = append(s.Messages, msg)
			_ = a.reportStatus(j.ID, "error", msg)
			continue
		}
		if ok, reason := looksLikeZPL([]byte(j.Zpl)); !ok {
			s.Failed++
			s.Messages = append(s.Messages, fmt.Sprintf("job %d: %s", j.ID, reason))
			_ = a.reportStatus(j.ID, "error", reason)
			continue
		}
		if err := printTCP(printerHost, printerPort, j.Zpl, j.Copies); err != nil {
			s.Failed++
			s.Messages = append(s.Messages, fmt.Sprintf("job %d: %v", j.ID, err))
			_ = a.reportStatus(j.ID, "error", err.Error())
			continue
		}
		s.Printed++
		_ = a.reportStatus(j.ID, "done", "")
	}
	return s.json(), nil
}
```

- [ ] **Step 2: Write `runonce_test.go`** (end-to-end: httptest server + printer listener)

```go
package mobilecore

import (
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
)

// printerSink accepts N connections and counts them.
func printerSink(t *testing.T, n int) (string, int, *int) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	count := 0
	var mu sync.Mutex
	go func() {
		for i := 0; i < n; i++ {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			io.ReadAll(conn)
			conn.Close()
			mu.Lock()
			count++
			mu.Unlock()
		}
		ln.Close()
	}()
	port := ln.Addr().(*net.TCPAddr).Port
	return "127.0.0.1", port, &count
}

func TestRunOnceMixed(t *testing.T) {
	// One valid job for our printer, one for a different printer, one non-ZPL.
	host, port, _ := printerSink(t, 1)

	var statuses sync.Map // id -> status
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/api/agent/jobs":
			io.WriteString(w, `{"jobs":[
				{"id":1,"printer":"Zebra-1","copies":1,"zpl":"^XA^XZ"},
				{"id":2,"printer":"Other","copies":1,"zpl":"^XA^XZ"},
				{"id":3,"printer":"Zebra-1","copies":1,"zpl":"%!PS not zpl"}
			]}`)
		default: // /api/agent/jobs/{id}/status
			var b map[string]any
			json.NewDecoder(r.Body).Decode(&b)
			var id int
			fmt.Sscanf(r.URL.Path, "/api/agent/jobs/%d/status", &id)
			statuses.Store(id, b["status"])
		}
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.1.0")
	out, err := a.RunOnce("Zebra-1", host, port)
	if err != nil {
		t.Fatal(err)
	}
	var s runSummary
	if err := json.Unmarshal([]byte(out), &s); err != nil {
		t.Fatalf("summary not JSON: %v (%s)", err, out)
	}
	if s.Polled != 3 || s.Printed != 1 || s.Failed != 2 {
		t.Fatalf("summary = %+v", s)
	}
	if v, _ := statuses.Load(1); v != "done" {
		t.Fatalf("job 1 status = %v, want done", v)
	}
	if v, _ := statuses.Load(2); v != "error" {
		t.Fatalf("job 2 status = %v, want error", v)
	}
	if v, _ := statuses.Load(3); v != "error" {
		t.Fatalf("job 3 status = %v, want error", v)
	}
}

func TestRunOnceAuthError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "bad", "0.1.0")
	out, err := a.RunOnce("Zebra-1", "127.0.0.1", 9100)
	if err == nil {
		t.Fatal("expected error")
	}
	var s runSummary
	json.Unmarshal([]byte(out), &s)
	if !s.AuthError {
		t.Fatalf("authError = false, want true (%s)", out)
	}
	if s.Messages == nil {
		t.Fatal("messages marshalled to null")
	}
}
```

- [ ] **Step 3: Run the full package with vet + gofmt**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/connector
gofmt -l mobilecore/
go vet ./mobilecore/...
go test ./mobilecore/... -v
```
Expected: `gofmt -l` prints nothing; `vet` clean; all tests PASS.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/mobilecore/runonce.go connector/mobilecore/runonce_test.go
git commit -m "feat(mobilecore): RunOnce poll-print cycle with JSON summary (F36)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Android module docs + version bump + release v0.19.0

**Files:**
- Create: `connector/android/README.md`
- Modify: `docs/PROJECT.md` (F36 row)
- Modify: `frontend/package.json`, `backend/pyproject.toml` (version), `CHANGELOG.md`

**Interfaces:**
- Consumes: the exported Go API from Tasks 2–3 (`NewAgent`, `RunOnce`, `ReportState`).
- Produces: tag `v0.19.0`, notes-only GitHub release (no APK — built off-device later).

- [ ] **Step 1: Write `connector/android/README.md`**

Create with this content (the Kotlin below is a **reference scaffold to build and verify on a machine with Android Studio — it is not compiled here**):

````markdown
# BarcodeLabelGen — konektor Android (F36)

Aplikacja mobilna, która działa jak `blg-connector`, ale na telefonie: pobiera
zadania z kolejki serwera i drukuje ZPL po RAW TCP 9100 do drukarki w tej samej
sieci WiFi. Bez fast-path localhost i bez wirtualnej drukarki (nie mają sensu na
Androidzie).

## Architektura

- **Rdzeń Go** `connector/mobilecore/` — cała logika sieć+druk, przetestowana
  (`go test ./connector/mobilecore/...`). Eksportuje pod gomobile:
  - `NewAgent(serverURL, token, agentVersion string) *Agent`
  - `(*Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error)`
    → JSON `{"polled","printed","failed","messages":[],"authError"}`
  - `(*Agent) ReportState(printerName, printerHost string, printerPort int) error`
- **AAR** — `gomobile bind` pakuje rdzeń dla Androida.
- **Powłoka Kotlin** — `PrintService` (foreground) woła `RunOnce` w pętli;
  `MainActivity` zbiera konfigurację i pokazuje status.

> **Status:** rdzeń Go jest zweryfikowany. Powłoka Kotlin i build AAR **nie były
> zbudowane ani uruchomione** przez autora — poniższe to instrukcje i scaffold do
> zbudowania oraz przetestowania na urządzeniu.

## Budowa AAR (maszyna z Android SDK + NDK)

```
go install golang.org/x/mobile/cmd/gomobile@latest
gomobile init
cd connector
gomobile bind -target=android -androidapi 21 -o blgcore.aar ./mobilecore
```

Skopiuj `blgcore.aar` do `app/libs/` modułu Android i dodaj w `build.gradle`:
`implementation files('libs/blgcore.aar')`. Pakiet Javy: `mobilecore`.

## Uprawnienia (`AndroidManifest.xml`)

```xml
<uses-permission android:name="android.permission.INTERNET" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE" />
<uses-permission android:name="android.permission.FOREGROUND_SERVICE_DATA_SYNC" />
<uses-permission android:name="android.permission.POST_NOTIFICATIONS" />
```

## Scaffold Kotlin (do zbudowania i weryfikacji na urządzeniu)

Konfiguracja (URL serwera, token, nazwa drukarki, IP, port=9100, interwał=15 s)
trzymana w Jetpack DataStore i czytana przez usługę.

```kotlin
// PrintService.kt — foreground service z pętlą poll-and-print.
import mobilecore.Agent
import mobilecore.Mobilecore  // gomobile: Mobilecore.newAgent(...)

class PrintService : Service() {
    private val scope = CoroutineScope(Dispatchers.IO + SupervisorJob())

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        startForeground(1, buildNotification("Nasłuch zadań…"))
        val cfg = loadConfig() // serverUrl, token, printerName, printerIp, port, intervalSec
        val agent: Agent = Mobilecore.newAgent(cfg.serverUrl, cfg.token, cfg.agentVersion)
        scope.launch {
            while (isActive) {
                try {
                    val summary = agent.runOnce(cfg.printerName, cfg.printerIp, cfg.port.toLong())
                    val s = JSONObject(summary)
                    if (s.getBoolean("authError")) {
                        updateNotification("Token odrzucony — odtwórz na stronie Urządzenia")
                        stopSelf(); break
                    }
                    updateNotification("Wydrukowano ${s.getInt("printed")}, błędy ${s.getInt("failed")}")
                } catch (e: Exception) {
                    updateNotification("Offline — ponawiam…")
                }
                delay(cfg.intervalSec * 1000L)
            }
        }
        return START_STICKY
    }
    // buildNotification / updateNotification / loadConfig / onBind omitted — implement per Android norms.
}
```

`MainActivity` to prosty formularz zapisujący konfigurację do DataStore i
przyciski Start/Stop dla `PrintService`, plus pole na ostatnie podsumowanie.

> **gomobile a typy:** `RunOnce`/`ReportState` przyjmują `int` po stronie Go →
> gomobile mapuje na `long` w Javie/Kotlinie (stąd `cfg.port.toLong()`). Zwrot
> `(string, error)` → Kotlin dostaje `String` i rzuca `Exception` na błąd cyklu.

## Test end-to-end (na urządzeniu)

1. W web appce wygeneruj zadanie druku skierowane na urządzenie/drukarkę.
2. Uruchom usługę w aplikacji (Start).
3. Zadanie powinno wydrukować się na drukarce w WiFi; status `done` widoczny w
   UI serwera (strona Urządzenia).

## Dystrybucja

MVP: APK w GitHub Releases (sideload w LAN). `versionName` startuje od `0.1.0`.
Google Play — opcjonalnie później.
````

- [ ] **Step 2: Mark F36 done in PROJECT.md**

In `docs/PROJECT.md`, find the `| F36 |` row and append to its description (before the trailing `| P2 |`): ` — **rdzeń zrealizowany w v0.19.0** (`connector/mobilecore/` + testy; powłoka Kotlin/AAR udokumentowana w `connector/android/README.md`, build i test na urządzeniu poza tą sesją)`.

- [ ] **Step 3: Bump versions**

Run:
```bash
cd /var/www/html/BarcodeLabelGen
sed -i 's/"version": "0.18.0"/"version": "0.19.0"/' frontend/package.json
sed -i '0,/^version = "0.18.0"/s//version = "0.19.0"/' backend/pyproject.toml
grep '"version"' frontend/package.json; grep -m1 '^version' backend/pyproject.toml
```
Expected: both `0.19.0`.

- [ ] **Step 4: Add the CHANGELOG section**

In `CHANGELOG.md`, insert directly above `## [0.18.0] — 2026-07-04`:

```markdown
## [0.19.0] — 2026-07-04

### Added
- **Android connector core (F36).** New `connector/mobilecore/` — a
  gomobile-friendly Go package (`NewAgent` / `RunOnce` / `ReportState`) that
  polls the job queue with a device token and prints ZPL over RAW TCP 9100,
  mirroring the desktop agent's contract. Fully unit-tested (poll parsing,
  Bearer auth, 401 handling, TCP print with copies/newline, printer-name
  match, non-ZPL rejection, end-to-end RunOnce summary). The Kotlin
  foreground-service shell and the `gomobile bind` AAR build are documented in
  `connector/android/README.md` for a machine with the Android toolchain — the
  APK is built and verified on-device in a later step (not in this release).
```

Then replace:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.18.0...HEAD
[0.18.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.18.0
```
with:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.19.0...HEAD
[0.19.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.19.0
[0.18.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.18.0
```

- [ ] **Step 5: Commit, tag, push**

```bash
cd /var/www/html/BarcodeLabelGen
git add connector/android/README.md docs/PROJECT.md frontend/package.json backend/pyproject.toml CHANGELOG.md
git commit -m "chore(release): v0.19.0 — Android connector core + shell docs (F36)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git tag -a v0.19.0 -m "v0.19.0 — Android connector core (F36)"
git push origin main && git push origin v0.19.0
```
Expected: pushed, tag on remote.

- [ ] **Step 6: Create the GitHub release (notes only — APK follows off-device)**

```bash
cd /var/www/html/BarcodeLabelGen
gh release create v0.19.0 \
  --title "v0.19.0 — Android connector core (F36)" \
  --notes "$(awk '/^## \[0.19.0\]/{f=1;next} /^## \[0.18.0\]/{f=0} f' CHANGELOG.md)

Connector desktop binaries are unchanged since v0.18.0. The Android APK will be attached in a later release once built on a machine with the Android toolchain (see connector/android/README.md)."
gh release view v0.19.0 --json tagName --jq .tagName
```
Expected: release URL printed; tag `v0.19.0`.

---

## Notes for the implementer

- **No web-app rebuild needed.** F36 adds a Go subpackage + docs; the Docker stack is untouched, so `tools/rebuild.sh` is not required.
- **Do not modify the desktop connector** (`connector/*.go`, package main). `mobilecore` is standalone by design.
- The Go core is the only verifiable-here artifact — Tasks 1–3 must be green (`go test ./connector/mobilecore/...`) before Task 4. Task 4 ships docs + version + release; it does not build an APK.
- If `go` reports a `min` builtin issue, note the module is Go 1.22 (`connector/go.mod`), where `min` is a language builtin — no import needed.
