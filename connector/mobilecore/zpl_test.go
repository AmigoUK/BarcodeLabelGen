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
