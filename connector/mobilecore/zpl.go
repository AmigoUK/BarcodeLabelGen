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
