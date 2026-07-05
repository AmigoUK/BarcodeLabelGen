package mobilecore

import (
	"encoding/json"
	"errors"
	"io"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestPollJobsParsesAndSendsBearer(t *testing.T) {
	var gotAuth string
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		gotAuth = r.Header.Get("Authorization")
		if r.Method != http.MethodGet || r.URL.Path != "/api/agent/jobs" {
			t.Errorf("unexpected %s %s", r.Method, r.URL.Path)
		}
		io.WriteString(w, `{"jobs":[{"id":7,"printer":"Zebra-1","copies":2,"zpl":"^XA^XZ"}]}`)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "blg_tok", "0.1.0")
	jobs, err := a.pollJobs()
	if err != nil {
		t.Fatal(err)
	}
	if gotAuth != "Bearer blg_tok" {
		t.Fatalf("auth header = %q", gotAuth)
	}
	if len(jobs) != 1 || jobs[0].ID != 7 || jobs[0].Copies != 2 || jobs[0].Printer != "Zebra-1" {
		t.Fatalf("jobs = %+v", jobs)
	}
}

func TestPollJobs401(t *testing.T) {
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusUnauthorized)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "bad", "0.1.0")
	_, err := a.pollJobs()
	if !errors.Is(err, errUnauthorized) {
		t.Fatalf("want errUnauthorized, got %v", err)
	}
}

func TestReportStatusBody(t *testing.T) {
	var body map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agent/jobs/7/status" {
			t.Errorf("path %s", r.URL.Path)
		}
		json.NewDecoder(r.Body).Decode(&body)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.1.0")
	if err := a.reportStatus(7, "error", "boom"); err != nil {
		t.Fatal(err)
	}
	if body["status"] != "error" || body["error"] != "boom" {
		t.Fatalf("body = %+v", body)
	}
}

func TestReportStateBody(t *testing.T) {
	var body map[string]any
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if r.URL.Path != "/api/agent/state" {
			t.Errorf("path %s", r.URL.Path)
		}
		json.NewDecoder(r.Body).Decode(&body)
	}))
	defer srv.Close()

	a := NewAgent(srv.URL, "t", "0.9.9")
	if err := a.ReportState("Zebra-1", "192.168.1.50", 9100); err != nil {
		t.Fatal(err)
	}
	if body["agent_version"] != "0.9.9" {
		t.Fatalf("agent_version = %v", body["agent_version"])
	}
	printers, ok := body["printers"].([]any)
	if !ok || len(printers) != 1 {
		t.Fatalf("printers = %v", body["printers"])
	}
	p := printers[0].(map[string]any)
	if p["name"] != "Zebra-1" || p["host"] != "192.168.1.50" || p["port"].(float64) != 9100 {
		t.Fatalf("printer = %+v", p)
	}
}
