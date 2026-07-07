//go:build windows

package main

import (
	"fmt"
	"strings"
	"unicode"
	"unicode/utf8"

	winprinter "github.com/alexbrainman/printer"
)

// validQueueName mirrors the server schema's AgentPrinter.name max_length
// (100 characters — Pydantic counts runes, not bytes) but is otherwise
// permissive: winspool takes the printer name as a plain string (no shell,
// no argv splitting), so parentheses, spaces, and non-ASCII (e.g. Polish
// diacritics) are all legal — only control characters are rejected as
// just-plain-weird.
func validQueueName(name string) bool {
	n := utf8.RuneCountInString(name)
	if n < 1 || n > 100 {
		return false
	}
	for _, r := range name {
		if unicode.IsControl(r) {
			return false
		}
	}
	return true
}

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
	if copies < 1 {
		copies = 1
	}
	p, err := winprinter.Open(queue)
	if err != nil {
		return fmt.Errorf("printer %s (local queue): %w", queue, err)
	}
	defer p.Close()
	if err := p.StartRawDocument("BarcodeLabelGen label"); err != nil {
		return fmt.Errorf("printer %s (local queue): %w", queue, err)
	}
	payload := strings.Repeat(ensureTrailingNewline(zpl), copies)
	if _, err := p.Write([]byte(payload)); err != nil {
		// Still tell the spooler we're done — ignore its error here, the
		// write failure is the one that matters.
		_ = p.EndDocument()
		return fmt.Errorf("printer %s (local queue): write: %w", queue, err)
	}
	if err := p.EndDocument(); err != nil {
		return fmt.Errorf("printer %s (local queue): end document: %w", queue, err)
	}
	return nil
}
