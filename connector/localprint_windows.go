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
