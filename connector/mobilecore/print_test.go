package mobilecore

import (
	"io"
	"net"
	"strings"
	"testing"
)

// acceptOne starts a listener, returns its host, port, and a channel that
// receives the bytes of the single connection it accepts.
func acceptOne(t *testing.T) (string, int, <-chan []byte) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	got := make(chan []byte, 1)
	go func() {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer ln.Close()
		defer conn.Close()
		b, _ := io.ReadAll(conn)
		got <- b
	}()
	host, portStr, _ := net.SplitHostPort(ln.Addr().String())
	port := ln.Addr().(*net.TCPAddr).Port
	_ = portStr
	return host, port, got
}

func TestPrintTCPRepeatsWithNewline(t *testing.T) {
	host, port, got := acceptOne(t)
	if err := printTCP(host, port, "^XA^XZ", 3); err != nil {
		t.Fatal(err)
	}
	b := <-got
	if want := strings.Repeat("^XA^XZ\n", 3); string(b) != want {
		t.Fatalf("got %q want %q", b, want)
	}
}

func TestPrintTCPClampsCopies(t *testing.T) {
	host, port, got := acceptOne(t)
	if err := printTCP(host, port, "^XA^XZ", 0); err != nil { // 0 -> 1
		t.Fatal(err)
	}
	b := <-got
	if want := "^XA^XZ\n"; string(b) != want {
		t.Fatalf("copies=0 got %q want one copy %q", b, want)
	}
}

func TestPrintTCPUnreachable(t *testing.T) {
	// Port 1 on loopback refuses quickly.
	if err := printTCP("127.0.0.1", 1, "^XA^XZ", 1); err == nil {
		t.Fatal("expected error dialing unreachable printer")
	}
}
