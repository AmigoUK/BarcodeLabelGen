package main

import (
	"context"
	"encoding/base64"
	"fmt"
	"io"
	"log"
	"net"
	"os"
	"path/filepath"
	"strings"
	"time"
)

const (
	// One printed job = one TCP connection (that's how Windows' Standard
	// TCP/IP port monitor spools) — read to EOF with an idle guard.
	captureIdleTimeout = 30 * time.Second
	captureMaxBytes    = 2 << 20 // 2 MB — driver bitmaps (^GFA) get big
	captureRetryEvery  = 30 * time.Second
)

// Capturer accepts virtual-printer connections, spools each job to disk
// and uploads it; failed uploads are retried from the spool, so captures
// survive server outages and agent restarts.
type Capturer struct {
	cfg    CaptureConfig
	client *Client
}

func NewCapturer(cfg CaptureConfig, client *Client) *Capturer {
	return &Capturer{cfg: cfg, client: client}
}

func (c *Capturer) Run(ctx context.Context) error {
	if err := os.MkdirAll(c.cfg.SpoolDir, 0o755); err != nil {
		return fmt.Errorf("capture spool dir: %w", err)
	}
	ln, err := net.Listen("tcp", c.cfg.Listen)
	if err != nil {
		return fmt.Errorf("capture listener: %w", err)
	}
	log.Printf("virtual printer listening on %s (spool: %s)", c.cfg.Listen, c.cfg.SpoolDir)

	go func() {
		<-ctx.Done()
		_ = ln.Close()
	}()
	go c.retryLoop(ctx)
	c.flushSpool() // anything left over from a previous run

	for {
		conn, err := ln.Accept()
		if err != nil {
			if ctx.Err() != nil {
				return nil
			}
			log.Printf("capture accept: %v", err)
			continue
		}
		go c.handleConn(conn)
	}
}

func (c *Capturer) handleConn(conn net.Conn) {
	defer conn.Close()
	_ = conn.SetReadDeadline(time.Now().Add(captureIdleTimeout))
	data, err := io.ReadAll(io.LimitReader(conn, captureMaxBytes+1))
	if err != nil && len(data) == 0 {
		log.Printf("capture read: %v", err)
		return
	}
	if len(data) == 0 {
		return // port monitor probe / empty connection
	}
	if len(data) > captureMaxBytes {
		log.Printf("capture dropped: job exceeds %d bytes", captureMaxBytes)
		return
	}
	if !strings.Contains(string(data), "^XA") {
		log.Printf("capture dropped: %d bytes without ^XA (non-ZPL driver?)", len(data))
		return
	}

	path := filepath.Join(c.cfg.SpoolDir,
		fmt.Sprintf("%s-%09d.zpl", time.Now().UTC().Format("20060102-150405"), time.Now().Nanosecond()))
	if err := os.WriteFile(path, data, 0o644); err != nil {
		log.Printf("capture spool write: %v", err)
		return
	}
	log.Printf("captured %d bytes from %s", len(data), conn.RemoteAddr())
	c.uploadFile(path)
}

func (c *Capturer) retryLoop(ctx context.Context) {
	ticker := time.NewTicker(captureRetryEvery)
	defer ticker.Stop()
	for {
		select {
		case <-ctx.Done():
			return
		case <-ticker.C:
			c.flushSpool()
		}
	}
}

func (c *Capturer) flushSpool() {
	entries, err := os.ReadDir(c.cfg.SpoolDir)
	if err != nil {
		return
	}
	for _, e := range entries {
		if e.IsDir() || !strings.HasSuffix(e.Name(), ".zpl") {
			continue
		}
		c.uploadFile(filepath.Join(c.cfg.SpoolDir, e.Name()))
	}
}

func (c *Capturer) uploadFile(path string) {
	data, err := os.ReadFile(path)
	if err != nil {
		return
	}
	if err := c.client.UploadCapture(data); err != nil {
		log.Printf("capture upload failed (kept in spool): %v", err)
		return
	}
	_ = os.Remove(path)
	log.Printf("capture uploaded (%d bytes)", len(data))
}

// UploadCapture sends a captured job, base64-encoded for safe JSON transport.
func (c *Client) UploadCapture(data []byte) error {
	body := map[string]any{"zpl_b64": base64.StdEncoding.EncodeToString(data)}
	return c.do("POST", "/api/agent/captures", body, nil)
}
