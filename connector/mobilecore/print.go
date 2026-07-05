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
