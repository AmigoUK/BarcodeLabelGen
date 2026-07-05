package mobilecore

import (
	"encoding/json"
	"fmt"
	"io"
	"net"
	"net/http"
	"net/http/httptest"
	"sync"
	"testing"
)

// printerSink accepts N connections and counts them.
func printerSink(t *testing.T, n int) (string, int, *int) {
	t.Helper()
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	count := 0
	var mu sync.Mutex
	go func() {
		for i := 0; i < n; i++ {
			conn, err := ln.Accept()
			if err != nil {
				return
			}
			io.ReadAll(conn)
			conn.Close()
			mu.Lock()
			count++
			mu.Unlock()
		}
		ln.Close()
	}()
	port := ln.Addr().(*net.TCPAddr).Port
	return "127.0.0.1", port, &count
}

func TestRunOnceMixed(t *testing.T) {
	// One valid job for our printer, one for a different printer, one non-ZPL.
	host, port, _ := printerSink(t, 1)

	var statuses sync.Map // id -> status
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		switch {
		case r.URL.Path == "/api/agent/jobs":
			io.WriteString(w, `{"jobs":[
				{"id":1,"printer":"Zebra-1","copies":1,"zpl":"^XA^XZ"},
				{"id":2,"printer":"Other","copies":1,"zpl":"^XA^XZ"},
				{"id":3,"printer":"Zebra-1","copies":1,"zpl":"%!PS not zpl"}
			]}`)
		default: // /api/agent/jobs/{id}/status
			var b map[string]any
			json.NewDecoder(r.Body).Decode(&b)
			var id int
			fmt.Sscanf(r.URL.Path, "/api/agent/jobs/%d/status", &id)
			statuses.Store(id, b["status"])
		}
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.1.0")
	out, err := a.RunOnce("Zebra-1", host, port)
	if err != nil {
		t.Fatal(err)
	}
	var s runSummary
	if err := json.Unmarshal([]byte(out), &s); err != nil {
		t.Fatalf("summary not JSON: %v (%s)", err, out)
	}
	if s.Polled != 3 || s.Printed != 1 || s.Failed != 2 {
		t.Fatalf("summary = %+v", s)
	}
	if v, _ := statuses.Load(1); v != "done" {
		t.Fatalf("job 1 status = %v, want done", v)
	}
	if v, _ := statuses.Load(2); v != "error" {
		t.Fatalf("job 2 status = %v, want error", v)
	}
	if v, _ := statuses.Load(3); v != "error" {
		t.Fatalf("job 3 status = %v, want error", v)
	}
}

func TestRunOnceAuthError(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "bad", "0.1.0")
	out, err := a.RunOnce("Zebra-1", "127.0.0.1", 9100)
	if err == nil {
		t.Fatal("expected error")
	}
	var s runSummary
	json.Unmarshal([]byte(out), &s)
	if !s.AuthError {
		t.Fatalf("authError = false, want true (%s)", out)
	}
	if s.Messages == nil {
		t.Fatal("messages marshalled to null")
	}
}
