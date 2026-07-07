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
