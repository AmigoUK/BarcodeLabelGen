package mobilecore

import (
	"encoding/json"
	"errors"
	"fmt"
)

type runSummary struct {
	Polled    int      `json:"polled"`
	Printed   int      `json:"printed"`
	Failed    int      `json:"failed"`
	Messages  []string `json:"messages"`
	AuthError bool     `json:"authError"`
}

func (s runSummary) json() string {
	// Messages must never marshal to null (Kotlin expects an array).
	if s.Messages == nil {
		s.Messages = []string{}
	}
	out, _ := json.Marshal(s)
	return string(out)
}

// RunOnce performs one poll → print → report cycle and returns a JSON summary.
// A job whose printer name != printerName is rejected (mirrors the desktop
// agent). The returned error is non-nil only for a whole-cycle failure (e.g.
// the poll itself failed); per-job failures are counted in Failed/Messages and
// reported to the server. On a 401 the summary's authError is true.
func (a *Agent) RunOnce(printerName, printerHost string, printerPort int) (string, error) {
	jobs, err := a.pollJobs()
	if err != nil {
		s := runSummary{AuthError: errors.Is(err, errUnauthorized)}
		return s.json(), err
	}
	s := runSummary{Polled: len(jobs)}
	for _, j := range jobs {
		if j.Printer != printerName {
			msg := fmt.Sprintf("job %d: printer %q not configured on this device", j.ID, j.Printer)
			s.Failed++
			s.Messages = append(s.Messages, msg)
			_ = a.reportStatus(j.ID, "error", msg)
			continue
		}
		if ok, reason := looksLikeZPL([]byte(j.Zpl)); !ok {
			s.Failed++
			s.Messages = append(s.Messages, fmt.Sprintf("job %d: %s", j.ID, reason))
			_ = a.reportStatus(j.ID, "error", reason)
			continue
		}
		if err := printTCP(printerHost, printerPort, j.Zpl, j.Copies); err != nil {
			s.Failed++
			s.Messages = append(s.Messages, fmt.Sprintf("job %d: %v", j.ID, err))
			_ = a.reportStatus(j.ID, "error", err.Error())
			continue
		}
		s.Printed++
		_ = a.reportStatus(j.ID, "done", "")
	}
	return s.json(), nil
}
