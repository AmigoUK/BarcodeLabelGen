package main

import (
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"
)

// LocalAPI is the loopback HTTP server (default 127.0.0.1:9110) used by the
// web app's fast path: the browser can print without the server round-trip.
// CORS is wide open — the server binds to loopback only, and Chrome's
// Private Network Access preflight gets the required header.
type LocalAPI struct {
	cfg *Config

	mu         sync.Mutex
	lastPoll   time.Time
	lastPollOK bool
}

func NewLocalAPI(cfg *Config) *LocalAPI { return &LocalAPI{cfg: cfg} }

func (a *LocalAPI) RecordPoll(ok bool) {
	a.mu.Lock()
	defer a.mu.Unlock()
	a.lastPoll = time.Now()
	a.lastPollOK = ok
}

func (a *LocalAPI) Handler() http.Handler {
	mux := http.NewServeMux()
	mux.HandleFunc("/status", a.withCORS(a.handleStatus))
	mux.HandleFunc("/printers", a.withCORS(a.handlePrinters))
	mux.HandleFunc("/print", a.withCORS(a.handlePrint))
	return mux
}

func (a *LocalAPI) withCORS(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Access-Control-Allow-Origin", "*")
		w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
		w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
		if r.Header.Get("Access-Control-Request-Private-Network") == "true" {
			w.Header().Set("Access-Control-Allow-Private-Network", "true")
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next(w, r)
	}
}

func (a *LocalAPI) handleStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	a.mu.Lock()
	lastPoll := a.lastPoll
	lastPollOK := a.lastPollOK
	a.mu.Unlock()

	names := make([]string, 0, len(a.cfg.Printers))
	for _, p := range a.cfg.Printers {
		names = append(names, p.Name)
	}
	payload := map[string]any{
		"agent":        "blg-connector",
		"version":      Version,
		"printers":     names,
		"last_poll_ok": lastPollOK,
	}
	if !lastPoll.IsZero() {
		payload["last_poll"] = lastPoll.UTC().Format(time.RFC3339)
	}
	writeJSON(w, http.StatusOK, payload)
}

func (a *LocalAPI) handlePrinters(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"printers": a.cfg.Printers})
}

func (a *LocalAPI) handlePrint(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "method not allowed", http.StatusMethodNotAllowed)
		return
	}
	var req struct {
		Printer string `json:"printer"`
		Zpl     string `json:"zpl"`
		Copies  int    `json:"copies"`
	}
	if err := json.NewDecoder(http.MaxBytesReader(w, r.Body, 1<<20)).Decode(&req); err != nil {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "bad_json"})
		return
	}
	if req.Zpl == "" {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "zpl_required"})
		return
	}
	printer, ok := a.cfg.PrinterByName(req.Printer)
	if !ok {
		writeJSON(w, http.StatusNotFound, map[string]any{"error": "printer_not_found"})
		return
	}
	if err := Print(printer, req.Zpl, req.Copies); err != nil {
		log.Printf("local print failed: %v", err)
		writeJSON(w, http.StatusBadGateway, map[string]any{"error": "print_failed", "detail": err.Error()})
		return
	}
	writeJSON(w, http.StatusOK, map[string]any{"ok": true})
}

func writeJSON(w http.ResponseWriter, status int, payload any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	_ = json.NewEncoder(w).Encode(payload)
}
