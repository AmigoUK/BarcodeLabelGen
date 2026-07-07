package main

import (
	"os"
	"path/filepath"
	"reflect"
	"strings"
	"testing"
)

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
