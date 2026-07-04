package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"net"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"strings"
	"testing"
	"time"
)

func writeConfig(t *testing.T, body string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "config.yaml")
	if err := os.WriteFile(path, []byte(body), 0o644); err != nil {
		t.Fatal(err)
	}
	return path
}

func TestLoadConfigDefaultsAndValidation(t *testing.T) {
	path := writeConfig(t, `
server_url: https://example.com/
token: blg_abc
printers:
  - name: Zebra-1
    host: 192.168.1.50
`)
	cfg, err := LoadConfig(path)
	if err != nil {
		t.Fatal(err)
	}
	if cfg.ServerURL != "https://example.com" {
		t.Errorf("trailing slash not trimmed: %q", cfg.ServerURL)
	}
	if cfg.Printers[0].Port != 9100 {
		t.Errorf("default port not applied: %d", cfg.Printers[0].Port)
	}
	if cfg.PollIntervalSeconds != 3 || cfg.Listen != "127.0.0.1:9110" {
		t.Errorf("defaults wrong: %+v", cfg)
	}
}

func TestLoadConfigRejectsBadToken(t *testing.T) {
	path := writeConfig(t, "server_url: https://x\ntoken: nope\nprinters: [{name: a, host: b}]\n")
	if _, err := LoadConfig(path); err == nil || !strings.Contains(err.Error(), "blg_") {
		t.Fatalf("expected token error, got %v", err)
	}
}

func TestPrintToTCPSendsCopies(t *testing.T) {
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	defer ln.Close()
	received := make(chan string, 1)
	go func() {
		conn, err := ln.Accept()
		if err != nil {
			return
		}
		defer conn.Close()
		buf := make([]byte, 4096)
		total := ""
		for {
			n, err := conn.Read(buf)
			total += string(buf[:n])
			if err != nil {
				break
			}
		}
		received <- total
	}()

	addr := ln.Addr().(*net.TCPAddr)
	p := Printer{Name: "fake", Host: "127.0.0.1", Port: addr.Port}
	if err := Print(p, "^XA^FDx^FS^XZ", 3); err != nil {
		t.Fatal(err)
	}
	got := <-received
	if strings.Count(got, "^XA") != 3 {
		t.Errorf("expected 3 copies, payload: %q", got)
	}
}

func TestPrintToFileSpools(t *testing.T) {
	dir := t.TempDir()
	p := Printer{Name: "spool", Host: "file://" + dir}
	if err := Print(p, "^XA^XZ", 2); err != nil {
		t.Fatal(err)
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 || !strings.HasSuffix(entries[0].Name(), ".zpl") {
		t.Fatalf("expected one .zpl file, got %v", entries)
	}
	raw, _ := os.ReadFile(filepath.Join(dir, entries[0].Name()))
	if strings.Count(string(raw), "^XA") != 2 {
		t.Errorf("expected 2 copies in spool, got %q", raw)
	}
}

func TestClientPollAndReport(t *testing.T) {
	var gotAuth, gotStatusBody string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		switch r.URL.Path {
		case "/api/agent/jobs":
			_ = json.NewEncoder(w).Encode(map[string]any{"jobs": []map[string]any{
				{"id": 7, "printer": "Zebra-1", "copies": 2, "zpl": "^XA^XZ"},
			}})
		case "/api/agent/jobs/7/status":
			raw := make([]byte, 200)
			n, _ := r.Body.Read(raw)
			gotStatusBody = string(raw[:n])
			_ = json.NewEncoder(w).Encode(map[string]any{"id": 7, "status": "done"})
		default:
			http.NotFound(w, r)
		}
	}))
	defer srv.Close()

	c := NewClient(srv.URL, "blg_test")
	jobs, err := c.PollJobs()
	if err != nil {
		t.Fatal(err)
	}
	if len(jobs) != 1 || jobs[0].ID != 7 || jobs[0].Copies != 2 {
		t.Fatalf("unexpected jobs: %+v", jobs)
	}
	if gotAuth != "Bearer blg_test" {
		t.Errorf("auth header: %q", gotAuth)
	}
	if err := c.ReportStatus(7, "done", ""); err != nil {
		t.Fatal(err)
	}
	if !strings.Contains(gotStatusBody, `"done"`) {
		t.Errorf("status body: %q", gotStatusBody)
	}
}

func TestClientUnauthorized(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()
	if _, err := NewClient(srv.URL, "blg_bad").PollJobs(); err == nil ||
		!strings.Contains(err.Error(), "401") {
		t.Fatalf("expected 401 error, got %v", err)
	}
}

func TestLocalAPIStatusAndPrint(t *testing.T) {
	dir := t.TempDir()
	cfg := &Config{
		ServerURL: "https://app.example.com:18003",
		Listen:    "127.0.0.1:0",
		Printers:  []Printer{{Name: "spool", Host: "file://" + dir}},
	}
	api := NewLocalAPI(cfg)
	api.RecordPoll(true)
	srv := httptest.NewServer(api.Handler())
	defer srv.Close()

	// status (no Origin — plain local tooling)
	resp, err := http.Get(srv.URL + "/status")
	if err != nil {
		t.Fatal(err)
	}
	var status map[string]any
	_ = json.NewDecoder(resp.Body).Decode(&status)
	if status["version"] != Version || status["last_poll_ok"] != true {
		t.Errorf("status: %v", status)
	}

	// allowed origin gets CORS + PNA headers on preflight
	req, _ := http.NewRequest(http.MethodOptions, srv.URL+"/print", nil)
	req.Header.Set("Origin", "https://app.example.com:18003")
	req.Header.Set("Access-Control-Request-Private-Network", "true")
	pre, _ := http.DefaultClient.Do(req)
	if pre.Header.Get("Access-Control-Allow-Origin") != "https://app.example.com:18003" {
		t.Error("missing CORS header for allowed origin")
	}
	if pre.Header.Get("Access-Control-Allow-Private-Network") != "true" {
		t.Error("missing PNA header on preflight")
	}

	// foreign origin is rejected outright — no drive-by print, no topology read
	reqEvil, _ := http.NewRequest(http.MethodGet, srv.URL+"/printers", nil)
	reqEvil.Header.Set("Origin", "https://evil.example")
	evil, _ := http.DefaultClient.Do(reqEvil)
	if evil.StatusCode != http.StatusForbidden {
		t.Errorf("foreign origin: HTTP %d, want 403", evil.StatusCode)
	}

	// print to the spool printer
	body := strings.NewReader(`{"printer":"spool","zpl":"^XA^XZ","copies":1}`)
	post, err := http.Post(srv.URL+"/print", "application/json", body)
	if err != nil {
		t.Fatal(err)
	}
	if post.StatusCode != http.StatusOK {
		t.Fatalf("print: HTTP %d", post.StatusCode)
	}
	entries, _ := os.ReadDir(dir)
	if len(entries) != 1 {
		t.Fatalf("expected spooled file, got %v", entries)
	}

	// non-JSON content type is rejected (blocks CORS "simple requests")
	simple, _ := http.Post(srv.URL+"/print", "text/plain",
		strings.NewReader(`{"printer":"spool","zpl":"^XA^XZ"}`))
	if simple.StatusCode != http.StatusUnsupportedMediaType {
		t.Errorf("text/plain: HTTP %d, want 415", simple.StatusCode)
	}

	// copies over the cap are rejected
	huge, _ := http.Post(srv.URL+"/print", "application/json",
		strings.NewReader(`{"printer":"spool","zpl":"^XA^XZ","copies":100000}`))
	if huge.StatusCode != http.StatusBadRequest {
		t.Errorf("huge copies: HTTP %d, want 400", huge.StatusCode)
	}

	// unknown printer
	post2, _ := http.Post(srv.URL+"/print", "application/json",
		strings.NewReader(`{"printer":"nope","zpl":"^XA^XZ"}`))
	if post2.StatusCode != http.StatusNotFound {
		t.Errorf("unknown printer: HTTP %d", post2.StatusCode)
	}
}

func TestCapturerSpoolsAndUploads(t *testing.T) {
	uploads := make(chan string, 4)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agent/captures" {
			http.NotFound(w, r)
			return
		}
		var body struct {
			ZplB64 string `json:"zpl_b64"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		raw, _ := base64.StdEncoding.DecodeString(body.ZplB64)
		uploads <- string(raw)
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{"capture":{"id":1}}`))
	}))
	defer srv.Close()

	spool := t.TempDir()
	cap := NewCapturer(CaptureConfig{Listen: "127.0.0.1:0", SpoolDir: spool}, NewClient(srv.URL, "blg_t"))

	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()
	// Run on a random port: start manually to learn the address.
	ln, err := net.Listen("tcp", "127.0.0.1:0")
	if err != nil {
		t.Fatal(err)
	}
	addr := ln.Addr().String()
	_ = ln.Close()
	cap.cfg.Listen = addr
	go func() { _ = cap.Run(ctx) }()
	time.Sleep(150 * time.Millisecond)

	// "Windows print": one connection, payload, close.
	conn, err := net.Dial("tcp", addr)
	if err != nil {
		t.Fatal(err)
	}
	_, _ = conn.Write([]byte("^XA^FDfrom-word^FS^XZ"))
	_ = conn.Close()

	select {
	case got := <-uploads:
		if !strings.Contains(got, "from-word") {
			t.Errorf("uploaded payload: %q", got)
		}
	case <-time.After(3 * time.Second):
		t.Fatal("capture was not uploaded")
	}
	// uploadFile removes the spool file after the HTTP call returns — poll.
	deadline := time.Now().Add(2 * time.Second)
	for {
		entries, _ := os.ReadDir(spool)
		if len(entries) == 0 {
			break
		}
		if time.Now().After(deadline) {
			t.Errorf("spool should be empty after upload, got %v", entries)
			break
		}
		time.Sleep(50 * time.Millisecond)
	}

	// Non-ZPL payload is dropped, not uploaded.
	conn2, _ := net.Dial("tcp", addr)
	_, _ = conn2.Write([]byte("%PDF-1.4 not zpl at all"))
	_ = conn2.Close()
	select {
	case got := <-uploads:
		t.Errorf("non-ZPL payload was uploaded: %q", got)
	case <-time.After(700 * time.Millisecond):
	}
}

func TestCapturerRetriesFromSpool(t *testing.T) {
	spool := t.TempDir()
	// Pre-existing spool file (e.g. server was down during a previous run).
	_ = os.WriteFile(filepath.Join(spool, "pending.zpl"), []byte("^XA^FDretry^FS^XZ"), 0o644)

	uploads := make(chan string, 1)
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		var body struct {
			ZplB64 string `json:"zpl_b64"`
		}
		_ = json.NewDecoder(r.Body).Decode(&body)
		raw, _ := base64.StdEncoding.DecodeString(body.ZplB64)
		uploads <- string(raw)
		w.WriteHeader(http.StatusCreated)
		_, _ = w.Write([]byte(`{}`))
	}))
	defer srv.Close()

	cap := NewCapturer(CaptureConfig{SpoolDir: spool}, NewClient(srv.URL, "blg_t"))
	cap.flushSpool()

	select {
	case got := <-uploads:
		if !strings.Contains(got, "retry") {
			t.Errorf("payload: %q", got)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("spooled capture was not uploaded")
	}
}

func TestUploadFileSkipsSymlinks(t *testing.T) {
	spool := t.TempDir()
	secret := filepath.Join(t.TempDir(), "secret.txt")
	_ = os.WriteFile(secret, []byte("^XA top secret ^XZ"), 0o600)
	_ = os.Symlink(secret, filepath.Join(spool, "evil.zpl"))

	uploaded := false
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, _ *http.Request) {
		uploaded = true
		w.WriteHeader(http.StatusCreated)
	}))
	defer srv.Close()

	cap := NewCapturer(CaptureConfig{SpoolDir: spool}, NewClient(srv.URL, "blg_t"))
	cap.flushSpool()
	if uploaded {
		t.Fatal("symlinked file must not be uploaded")
	}
	if _, err := os.Lstat(filepath.Join(spool, "evil.zpl")); err != nil {
		t.Fatal("symlink itself should not be removed")
	}
}

func TestDefaultSpoolDirIsUserScoped(t *testing.T) {
	dir := defaultSpoolDir()
	if strings.HasPrefix(dir, os.TempDir()) && !strings.Contains(dir, "blg-connector-captures-") {
		t.Errorf("default spool in shared temp without uid suffix: %s", dir)
	}
}
