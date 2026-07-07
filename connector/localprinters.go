package main

import (
	"regexp"
	"sync"
)

// Queue names reach `lp -d <name>` / winspool as a single exec arg, so shell
// injection is impossible — this allow-list guards against CUPS-invalid and
// just-plain-weird names slipping into job errors and the UI.
var queueNameRE = regexp.MustCompile(`^[A-Za-z0-9_.+-]{1,127}$`)

func validQueueName(name string) bool { return queueNameRE.MatchString(name) }

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
// server schema (1–65535); it is never dialed.
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
		out = append(out, Printer{Name: name, Kind: KindLocal, Port: 9100})
	}
	return out
}
