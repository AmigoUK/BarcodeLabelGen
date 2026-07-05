package mobilecore

import (
	"bytes"
	"encoding/json"
	"errors"
	"fmt"
	"io"
	"net/http"
	"time"
)

// errUnauthorized is returned when the server rejects the device token (401),
// so RunOnce can surface authError to the Kotlin shell.
var errUnauthorized = errors.New("device token rejected (401)")

// Agent talks to the BarcodeLabelGen agent API with a device token. It is the
// gomobile-bound entry point; construct it with NewAgent.
type Agent struct {
	serverURL    string
	token        string
	agentVersion string
	http         *http.Client
}

// NewAgent creates an Agent. gomobile binds this as a constructor.
func NewAgent(serverURL, token, agentVersion string) *Agent {
	return &Agent{
		serverURL:    serverURL,
		token:        token,
		agentVersion: agentVersion,
		http:         &http.Client{Timeout: 15 * time.Second},
	}
}

type job struct {
	ID      int    `json:"id"`
	Printer string `json:"printer"`
	Copies  int    `json:"copies"`
	Zpl     string `json:"zpl"`
}

func (a *Agent) do(method, path string, body any, out any) error {
	var reader io.Reader
	if body != nil {
		buf, err := json.Marshal(body)
		if err != nil {
			return err
		}
		reader = bytes.NewReader(buf)
	}
	req, err := http.NewRequest(method, a.serverURL+path, reader)
	if err != nil {
		return err
	}
	req.Header.Set("Authorization", "Bearer "+a.token)
	if body != nil {
		req.Header.Set("Content-Type", "application/json")
	}
	resp, err := a.http.Do(req)
	if err != nil {
		return err
	}
	defer resp.Body.Close()
	if resp.StatusCode == http.StatusUnauthorized {
		return errUnauthorized
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

func (a *Agent) pollJobs() ([]job, error) {
	var payload struct {
		Jobs []job `json:"jobs"`
	}
	if err := a.do(http.MethodGet, "/api/agent/jobs", nil, &payload); err != nil {
		return nil, err
	}
	return payload.Jobs, nil
}

func (a *Agent) reportStatus(id int, status, errMsg string) error {
	body := map[string]any{"status": status}
	if errMsg != "" {
		body["error"] = errMsg
	}
	return a.do(http.MethodPost, fmt.Sprintf("/api/agent/jobs/%d/status", id), body, nil)
}

func (a *Agent) reportState(name, host string, port int) error {
	body := map[string]any{
		"agent_version": a.agentVersion,
		"printers":      []map[string]any{{"name": name, "host": host, "port": port}},
	}
	return a.do(http.MethodPost, "/api/agent/state", body, nil)
}

// ReportState sends a heartbeat with the single configured printer. gomobile
// binds this; the Kotlin shell calls it periodically.
func (a *Agent) ReportState(printerName, printerHost string, printerPort int) error {
	return a.reportState(printerName, printerHost, printerPort)
}
