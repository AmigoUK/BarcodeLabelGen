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
	ctx, cancel := context.WithTimeout(context.Background(), printTimeout)
	defer cancel()
	out, err := exec.CommandContext(ctx, "lpstat", "-e").Output()
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
	if copies < 1 {
		copies = 1
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
