package main

import (
	"fmt"
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

func TestValidQueueName(t *testing.T) {
	valid := []string{"Zebra_ZD421", "HP.LaserJet-2", "a", "Q+plus", "has space"}
	for _, n := range valid {
		if !validQueueName(n) {
			t.Errorf("validQueueName(%q) = false, want true", n)
		}
	}
	invalid := []string{"", "slash/name", "hash#name", "semi;colon",
		"dollar$", "back`tick", string(make([]byte, 200)), " leading", "trailing "}
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

func TestMergedPrintersRespectsSchemaLimits(t *testing.T) {
	cfg := &Config{Printers: []Printer{
		{Name: "drukarka", Host: "192.168.1.50", Port: 9100},
		{Name: "spool", Host: "file:///tmp/x"},
	}}

	discovered := make([]string, 0, 62)
	for i := range 60 {
		discovered = append(discovered, fmt.Sprintf("Q%02d", i))
	}
	discovered = append(discovered, strings.Repeat("x", 101)) // over the 100-char name cap
	discovered = append(discovered, "Q00")                    // duplicate within the discovered list

	got := mergedPrinters(cfg, discovered)

	if len(got) != maxPrinters {
		t.Fatalf("len = %d, want %d (schema cap)", len(got), maxPrinters)
	}
	if got[0].Name != "drukarka" || got[1].Name != "spool" {
		t.Fatalf("config printers must win the first slots: %+v, %+v", got[0], got[1])
	}

	seen := map[string]int{}
	for _, p := range got {
		seen[p.Name]++
	}
	if seen["Q00"] != 1 {
		t.Errorf("duplicated discovered name appears %d times, want 1", seen["Q00"])
	}
	if seen[strings.Repeat("x", 101)] != 0 {
		t.Error("a 101-char discovered name must be skipped, not just truncated in")
	}
}

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
echo "bad/name"
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

func TestLocalPrintersRefreshKeepsSnapshotOnError(t *testing.T) {
	var l LocalPrinters
	l.set([]string{"Zebra_ZD421"})

	dir := t.TempDir()
	fakeBin(t, dir, "lpstat", `exit 1`)
	t.Setenv("PATH", dir+string(os.PathListSeparator)+os.Getenv("PATH"))

	l.Refresh()
	if !l.Has("Zebra_ZD421") {
		t.Fatal("failed Refresh must keep the previous snapshot")
	}
}

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
