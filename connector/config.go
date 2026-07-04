package main

import (
	"fmt"
	"os"
	"strings"
	"time"

	"gopkg.in/yaml.v3"
)

// Printer is a ZPL target. Host is either an IP/hostname (RAW TCP, JetDirect)
// or a `file:///path/to/dir` URL — then jobs are spooled as .zpl files, which
// doubles as the simulated-printer mode for testing without hardware.
type Printer struct {
	Name string `yaml:"name" json:"name"`
	Host string `yaml:"host" json:"host"`
	Port int    `yaml:"port" json:"port"`
}

func (p Printer) IsFile() bool { return strings.HasPrefix(p.Host, "file://") }

type Config struct {
	ServerURL                string    `yaml:"server_url"`
	Token                    string    `yaml:"token"`
	PollIntervalSeconds      int       `yaml:"poll_interval_seconds"`
	HeartbeatIntervalSeconds int       `yaml:"heartbeat_interval_seconds"`
	Listen                   string    `yaml:"listen"`
	Printers                 []Printer `yaml:"printers"`
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
	return cfg, nil
}
