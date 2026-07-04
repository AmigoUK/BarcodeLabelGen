package main

import (
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"net/http"
	"time"
)

// Client talks to the BarcodeLabelGen agent API with the device token.
type Client struct {
	baseURL string
	token   string
	http    *http.Client
}

func NewClient(baseURL, token string) *Client {
	return &Client{baseURL: baseURL, token: token, http: &http.Client{Timeout: 15 * time.Second}}
}

// Job mirrors the AgentJobPayload schema.
type Job struct {
	ID      int    `json:"id"`
	Printer string `json:"printer"`
	Copies  int    `json:"copies"`
	Zpl     string `json:"zpl"`
}

func (c *Client) do(method, path string, body any, out any) error {
	var reader io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return err
		}
		reader = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, c.baseURL+path, reader)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+c.token)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := c.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusUnauthorized {
		return fmt.Errorf("server rejected the device token (401) — recreate it on the Devices page")
	}
	if resp.StatusCode >= 400 {
		snippet, _ := io.ReadAll(io.LimitReader(resp.Body, 500))
		return fmt.Errorf("%s %s: HTTP %d: %s", method, path, resp.StatusCode, snippet)
	}
	if out != nil {
		return json.NewDecoder(resp.Body).Decode(out)
	}
	return nil
}

// PollJobs claims pending jobs for this device (server marks them `sent`).
func (c *Client) PollJobs() ([]Job, error) {
	var payload struct {
		Jobs []Job `json:"jobs"`
	}
	if err := c.do(http.MethodGet, "/api/agent/jobs", nil, &payload); err != nil {
		return nil, err
	}
	return payload.Jobs, nil
}

func (c *Client) ReportStatus(jobID int, status, errMsg string) error {
	body := map[string]any{"status": status}
	if errMsg != "" {
		body["error"] = errMsg
	}
	return c.do(http.MethodPost, fmt.Sprintf("/api/agent/jobs/%d/status", jobID), body, nil)
}

func (c *Client) ReportState(version string, printers []Printer) error {
	body := map[string]any{"agent_version": version, "printers": printers}
	return c.do(http.MethodPost, "/api/agent/state", body, nil)
}
