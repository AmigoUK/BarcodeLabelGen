// blg-connector — local print agent for BarcodeLabelGen.
//
// Polls the web app's queue for ZPL jobs and forwards them to label
// printers over RAW TCP 9100 (Zebra / JetDirect compatible), reports
// results, and exposes a loopback HTTP API for the browser fast path.
//
// Usage:
//
//	blg-connector -config /etc/blg-connector/config.yaml
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os/signal"
	"runtime"
	"syscall"
	"time"
)

// defaultConfigPath is the per-OS system location a service (LaunchDaemon /
// systemd / Windows service) reads when -config isn't given.
func defaultConfigPath() string {
	switch runtime.GOOS {
	case "windows":
		return `C:\ProgramData\blg-connector\config.yaml`
	case "darwin":
		return "/Library/Application Support/blg-connector/config.yaml"
	default: // linux, *bsd, …
		return "/etc/blg-connector/config.yaml"
	}
}

func main() {
	configPath := flag.String("config", defaultConfigPath(), "path to config.yaml")
	showVersion := flag.Bool("version", false, "print version and exit")
	flag.Parse()

	if *showVersion {
		fmt.Println("blg-connector", Version)
		return
	}

	cfg, err := LoadConfig(*configPath)
	if err != nil {
		log.Fatalf("config: %v", err)
	}

	client := NewClient(cfg.ServerURL, cfg.Token)

	local := &LocalPrinters{}
	if err := local.Refresh(); err != nil {
		log.Printf("printer discovery unavailable: %v", err)
	}
	localAPI := NewLocalAPI(cfg, local)

	server := &http.Server{Addr: cfg.Listen, Handler: localAPI.Handler(), ReadHeaderTimeout: 5 * time.Second}
	go func() {
		log.Printf("local API listening on http://%s", cfg.Listen)
		if err := server.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("local API: %v", err)
		}
	}()

	ctx, stop := signal.NotifyContext(context.Background(), syscall.SIGINT, syscall.SIGTERM)
	defer stop()

	go func() {
		t := time.NewTicker(60 * time.Second)
		defer t.Stop()
		for {
			select {
			case <-ctx.Done():
				return
			case <-t.C:
				_ = local.Refresh()
			}
		}
	}()

	if cfg.Capture.Listen != "" {
		capturer := NewCapturer(cfg.Capture, client)
		go func() {
			if err := capturer.Run(ctx); err != nil {
				log.Fatalf("capture: %v", err)
			}
		}()
	}

	heartbeat := func() {
		if err := client.ReportState(Version, mergedPrinters(cfg, local.Snapshot())); err != nil {
			log.Printf("heartbeat failed: %v", err)
		}
	}

	processJobs := func() {
		jobs, err := client.PollJobs()
		localAPI.RecordPoll(err == nil)
		if err != nil {
			log.Printf("poll failed: %v", err)
			return
		}
		for _, job := range jobs {
			printer, ok := resolvePrinter(cfg, local, job.Printer)
			if !ok {
				log.Printf("job %d: unknown printer %q", job.ID, job.Printer)
				_ = client.ReportStatus(job.ID, "error", fmt.Sprintf("printer %q not available on this device", job.Printer))
				continue
			}
			if err := Print(printer, job.Zpl, job.Copies); err != nil {
				log.Printf("job %d: print failed: %v", job.ID, err)
				_ = client.ReportStatus(job.ID, "error", err.Error())
				continue
			}
			log.Printf("job %d: printed on %s (%d copies)", job.ID, printer.Name, job.Copies)
			if err := client.ReportStatus(job.ID, "done", ""); err != nil {
				log.Printf("job %d: status report failed: %v", job.ID, err)
			}
		}
	}

	log.Printf("blg-connector %s → %s (%d printers, %d local queues, poll %s)",
		Version, cfg.ServerURL, len(cfg.Printers), len(local.Snapshot()), cfg.PollInterval())
	heartbeat()
	processJobs()

	pollTicker := time.NewTicker(cfg.PollInterval())
	heartbeatTicker := time.NewTicker(cfg.HeartbeatInterval())
	defer pollTicker.Stop()
	defer heartbeatTicker.Stop()

	for {
		select {
		case <-ctx.Done():
			log.Print("shutting down")
			shutdownCtx, cancel := context.WithTimeout(context.Background(), 3*time.Second)
			defer cancel()
			_ = server.Shutdown(shutdownCtx)
			return
		case <-pollTicker.C:
			processJobs()
		case <-heartbeatTicker.C:
			heartbeat()
		}
	}
}
