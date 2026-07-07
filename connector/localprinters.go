package main

import "sync"

// maxPrinters and maxPrinterNameLen mirror the server schema
// (AgentStateRequest.printers max_length=50, AgentPrinter.name max_length=100)
// so a device with many discovered queues can't be rejected wholesale.
const (
	maxPrinters       = 50
	maxPrinterNameLen = 100
)

// LocalPrinters is a concurrency-safe cache of system print queue names,
// refreshed by a ticker in main and read by the heartbeat + job resolution.
type LocalPrinters struct {
	mu    sync.Mutex
	names []string
}

func (l *LocalPrinters) set(names []string) {
	l.mu.Lock()
	defer l.mu.Unlock()
	l.names = append([]string(nil), names...)
}

func (l *LocalPrinters) Snapshot() []string {
	l.mu.Lock()
	defer l.mu.Unlock()
	return append([]string(nil), l.names...)
}

func (l *LocalPrinters) Has(name string) bool {
	l.mu.Lock()
	defer l.mu.Unlock()
	for _, n := range l.names {
		if n == name {
			return true
		}
	}
	return false
}

// mergedPrinters is what ReportState and the local API expose: config
// printers (kind computed from host, YAML wins name clashes) + discovered
// system queues as kind=local. Port 9100 on locals only satisfies the
// server schema (1–65535); it is never dialed. The result respects the
// server schema limits: AgentPrinter.name max 100 chars, AgentStateRequest
// max 50 printers — config printers are added first, so they always win a
// spot; overlong or overflow discovered names are dropped rather than
// causing the whole report to be rejected.
func mergedPrinters(cfg *Config, local []string) []Printer {
	out := make([]Printer, 0, len(cfg.Printers)+len(local))
	seen := make(map[string]bool, len(cfg.Printers))
	for _, p := range cfg.Printers {
		p.Kind = kindForHost(p.Host)
		if p.Port == 0 {
			p.Port = 9100
		}
		out = append(out, p)
		seen[p.Name] = true
	}
	for _, name := range local {
		if seen[name] {
			continue
		}
		if len(name) > maxPrinterNameLen {
			continue
		}
		seen[name] = true
		out = append(out, Printer{Name: name, Kind: KindLocal, Port: 9100})
	}
	if len(out) > maxPrinters {
		out = out[:maxPrinters]
	}
	return out
}

// resolvePrinter finds a job's target: config printers win, then any
// currently-discovered system queue prints as kind=local.
func resolvePrinter(cfg *Config, local *LocalPrinters, name string) (Printer, bool) {
	if p, ok := cfg.PrinterByName(name); ok {
		p.Kind = kindForHost(p.Host)
		return p, true
	}
	if local.Has(name) {
		return Printer{Name: name, Kind: KindLocal, Port: 9100}, true
	}
	return Printer{}, false
}

// Refresh re-reads the system queues. Errors (no CUPS, no lpstat) leave the
// previous snapshot untouched — a discovery hiccup must not unlist printers
// that jobs may be in flight for; a missing subsystem simply yields nothing.
// The error is returned so callers can log it (once, at startup) without
// affecting this invariant.
func (l *LocalPrinters) Refresh() error {
	names, err := listSystemPrinters()
	if err != nil {
		return err
	}
	l.set(names)
	return nil
}
