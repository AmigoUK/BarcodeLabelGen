package main

import (
	"fmt"
	"net"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const printTimeout = 10 * time.Second

// Print sends the ZPL to the printer `copies` times. TCP printers get one
// connection with the payload repeated (JetDirect / RAW 9100); file://
// printers spool one .zpl per call — the simulated-printer mode.
func Print(p Printer, zpl string, copies int) error {
	if copies < 1 {
		copies = 1
	}
	if p.IsFile() {
		return printToFile(p, zpl, copies)
	}
	return printToTCP(p, zpl, copies)
}

func printToTCP(p Printer, zpl string, copies int) error {
	addr := net.JoinHostPort(p.Host, fmt.Sprintf("%d", p.Port))
	conn, err := net.DialTimeout("tcp", addr, printTimeout)
	if err != nil {
		return fmt.Errorf("printer %s (%s): %w", p.Name, addr, err)
	}
	defer conn.Close()
	_ = conn.SetWriteDeadline(time.Now().Add(printTimeout))
	payload := strings.Repeat(ensureTrailingNewline(zpl), copies)
	if _, err := conn.Write([]byte(payload)); err != nil {
		return fmt.Errorf("printer %s (%s): write: %w", p.Name, addr, err)
	}
	return nil
}

func printToFile(p Printer, zpl string, copies int) error {
	dir := strings.TrimPrefix(p.Host, "file://")
	if err := os.MkdirAll(dir, 0o755); err != nil {
		return fmt.Errorf("printer %s: %w", p.Name, err)
	}
	now := time.Now().UTC()
	name := fmt.Sprintf("%s-%09d.zpl", now.Format("20060102-150405"), now.Nanosecond())
	path := filepath.Join(dir, name)
	payload := strings.Repeat(ensureTrailingNewline(zpl), copies)
	if err := os.WriteFile(path, []byte(payload), 0o644); err != nil {
		return fmt.Errorf("printer %s: %w", p.Name, err)
	}
	return nil
}

func ensureTrailingNewline(s string) string {
	if strings.HasSuffix(s, "\n") {
		return s
	}
	return s + "\n"
}
