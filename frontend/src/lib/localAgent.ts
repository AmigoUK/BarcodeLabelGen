/**
 * Browser fast path to the blg-connector's loopback API (F21).
 *
 * http://127.0.0.1 is a "potentially trustworthy" origin, so an HTTPS page
 * may fetch it without mixed-content blocking; Chrome additionally sends a
 * Private Network Access preflight, which the agent answers. Anything that
 * fails (no agent, browser policy, timeout) resolves to "not available"
 * and the print dialog silently falls back to the server queue.
 */

const AGENT_URL = "http://127.0.0.1:9110";
const PROBE_TIMEOUT_MS = 1500;

export type LocalAgentStatus = {
  agent: string;
  version: string;
  printers: string[];
  last_poll_ok: boolean;
};

export type LocalPrinter = {
  name: string;
  host: string;
  port: number;
};

async function agentFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const response = await fetch(`${AGENT_URL}${path}`, { ...init, signal: controller.signal });
    if (!response.ok) {
      const body = (await response.json().catch(() => ({}))) as { error?: string };
      throw new Error(body.error ?? `agent HTTP ${response.status}`);
    }
    return (await response.json()) as T;
  } finally {
    clearTimeout(timer);
  }
}

/** Null when no agent is reachable on this machine (the common case). */
export async function probeLocalAgent(): Promise<LocalAgentStatus | null> {
  try {
    return await agentFetch<LocalAgentStatus>("/status");
  } catch {
    return null;
  }
}

export async function fetchLocalPrinters(): Promise<LocalPrinter[]> {
  const body = await agentFetch<{ printers: LocalPrinter[] }>("/printers");
  return body.printers;
}

export async function printLocal(printer: string, zpl: string, copies: number): Promise<void> {
  await agentFetch("/print", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ printer, zpl, copies }),
  });
}
