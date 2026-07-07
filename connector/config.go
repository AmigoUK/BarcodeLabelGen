package main

import (
	"fmt"
	"os"
	"path/filepath"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// Printer is a print target. Host is an IP/hostname (RAW TCP, JetDirect),
// a `file:///path/to/dir` URL (spool-to-disk simulated printer), or empty
// for Kind==KindLocal — a system print queue discovered at runtime.
type Printer struct {
	Name string `yaml:"name" json:"name"`
	Host string `yaml:"host" json:"host"`
	Port int    `yaml:"port" json:"port"`
	// Kind is computed, never read from YAML: network | file | local.
	Kind string `yaml:"-" json:"kind"`
}

const (
	KindNetwork = "network"
	KindFile    = "file"
	KindLocal   = "local"
)

func kindForHost(host string) string {
	if strings.HasPrefix(host, "file://") {
		return KindFile
	}
	return KindNetwork
}

func (p Printer) IsFile() bool { return strings.HasPrefix(p.Host, "file://") }

// CaptureConfig enables the virtual-printer listener: a print queue pointed
// at this TCP port turns another app's ZPL output into a captured job.
// Windows: Standard TCP/IP port → 127.0.0.1:9101 with a ZDesigner driver.
// macOS/Linux: a CUPS raw queue → socket://127.0.0.1:9101 (see README).
type CaptureConfig struct {
	Listen   string `yaml:"listen"`    // empty = capture disabled
	SpoolDir string `yaml:"spool_dir"` // pending uploads survive restarts
}

type Config struct {
	ServerURL                string        `yaml:"server_url"`
	Token                    string        `yaml:"token"`
	PollIntervalSeconds      int           `yaml:"poll_interval_seconds"`
	HeartbeatIntervalSeconds int           `yaml:"heartbeat_interval_seconds"`
	Listen                   string        `yaml:"listen"`
	Printers                 []Printer     `yaml:"printers"`
	Capture                  CaptureConfig `yaml:"capture"`
}

func (c *Config) PollInterval() time.Duration {
	return time.Duration(c.PollIntervalSeconds) * time.Second
}

func (c *Config) HeartbeatInterval() time.Duration {
	return time.Duration(c.HeartbeatIntervalSeconds) * time.Second
}

func (c *Config) PrinterByName(name string) (Printer, bool) {
	for _, p := range c.Printers {
		if p.Name == name {
			return p, true
		}
	}
	return Printer{}, false
}

func LoadConfig(path string) (*Config, error) {
	raw, err := os.ReadFile(path)
	if err != nil {
		return nil, err
	}
	cfg := &Config{
		PollIntervalSeconds:      3,
		HeartbeatIntervalSeconds: 60,
		Listen:                   "127.0.0.1:9110",
	}
	if err := yaml.Unmarshal(raw, cfg); err != nil {
		return nil, fmt.Errorf("parsing %s: %w", path, err)
	}
	cfg.ServerURL = strings.TrimRight(cfg.ServerURL, "/")
	if cfg.ServerURL == "" {
		return nil, fmt.Errorf("%s: server_url is required", path)
	}
	if !strings.HasPrefix(cfg.Token, "blg_") {
		return nil, fmt.Errorf("%s: token must start with blg_ (create one on the Devices page)", path)
	}
	if len(cfg.Printers) == 0 {
		return nil, fmt.Errorf("%s: define at least one printer", path)
	}
	for i, p := range cfg.Printers {
		if p.Name == "" || p.Host == "" {
			return nil, fmt.Errorf("%s: printers[%d] needs name and host", path, i)
		}
		if p.Port == 0 && !p.IsFile() {
			cfg.Printers[i].Port = 9100
		}
	}
	if cfg.PollIntervalSeconds < 1 {
		cfg.PollIntervalSeconds = 3
	}
	if cfg.HeartbeatIntervalSeconds < 10 {
		cfg.HeartbeatIntervalSeconds = 60
	}
	if cfg.Capture.Listen != "" && cfg.Capture.SpoolDir == "" {
		cfg.Capture.SpoolDir = defaultSpoolDir()
	}
	return cfg, nil
}

// defaultSpoolDir lives under the user's cache dir, not the world-writable
// system temp — captured jobs are private and the spool must not accept
// files planted by other local users (they'd be uploaded with our token).
func defaultSpoolDir() string {
	if base, err := os.UserCacheDir(); err == nil {
		return filepath.Join(base, "blg-connector", "captures")
	}
	return filepath.Join(os.TempDir(), fmt.Sprintf("blg-connector-captures-%d", os.Getuid()))
}
