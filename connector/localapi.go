package main

import (
	"encoding/json"
	"log"
	"net/http"
	"net/url"
	"strings"
	"sync"
	"time"
)

// LocalAPI is the loopback HTTP server (default 127.0.0.1:9110) used by the
// web app's fast path: the browser can print without the server round-trip.
// CORS allows only the configured server's origin — any other website in a
// local browser must not be able to drive-by print or read printer IPs.
// Chrome's Private Network Access preflight gets the required header.
type LocalAPI struct {
	cfg           *Config
	allowedOrigin string

	mu         sync.Mutex
	lastPoll   time.Time
	lastPollOK bool
}

func NewLocalAPI(cfg *Config) *LocalAPI {
	return &LocalAPI{cfg: cfg, allowedOrigin: originOf(cfg.ServerURL)}
}

// originOf reduces a URL to scheme://host[:port] for CORS matching.
func originOf(rawURL string) string {
	u, err := url.Parse(rawURL)
	if err != nil || u.Scheme == "" || u.Host == "" {
		return ""
	}
	return u.Scheme + "://" + u.Host
}

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
		origin := r.Header.Get("Origin")
		if origin != "" {
			// Browser request: only the web app's origin may call us.
			if a.allowedOrigin == "" || origin != a.allowedOrigin {
				http.Error(w, "origin not allowed", http.StatusForbidden)
				return
			}
			w.Header().Set("Access-Control-Allow-Origin", a.allowedOrigin)
			w.Header().Set("Vary", "Origin")
			w.Header().Set("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Content-Type")
			if r.Header.Get("Access-Control-Request-Private-Network") == "true" {
				w.Header().Set("Access-Control-Allow-Private-Network", "true")
			}
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
	// Requiring application/json means a cross-site form/fetch can't reach
	// this as a "simple request" — the browser preflights, and preflight is
	// gated on the allowed origin above.
	if ct := r.Header.Get("Content-Type"); !strings.HasPrefix(ct, "application/json") {
		writeJSON(w, http.StatusUnsupportedMediaType, map[string]any{"error": "json_required"})
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
	if ok, reason := looksLikeZPL([]byte(req.Zpl)); !ok {
		writeJSON(w, http.StatusUnprocessableEntity,
			map[string]any{"error": "invalid_zpl", "detail": reason})
		return
	}
	if req.Copies < 1 {
		req.Copies = 1
	}
	if req.Copies > MaxCopies {
		writeJSON(w, http.StatusBadRequest, map[string]any{"error": "too_many_copies", "max": MaxCopies})
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
