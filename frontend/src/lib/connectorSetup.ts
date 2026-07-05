/**
 * Pure helpers for the "Connect a printer" wizard (F38): detect the user's OS,
 * pick the right connector binary, build a ready-to-run config.yaml, and the
 * one-line start command. No React, no I/O — everything a step needs is a
 * plain string, so the wizard never edits files by hand.
 */

export type ConnectorOS =
  | "mac-apple"
  | "mac-intel"
  | "windows"
  | "linux-amd64"
  | "linux-arm64"
  | "linux-arm";

export type OSDetection = {
  os: ConnectorOS | null;
  family: "mac" | "windows" | "linux" | null;
  /** Apple Silicon vs Intel can't be told apart in a browser — ask the user. */
  macNeedsChipChoice: boolean;
};

export type PrinterChoice = { mode: "test" } | { mode: "ip"; ip: string; port?: number };

const ASSET: Record<ConnectorOS, string> = {
  "mac-apple": "blg-connector-macos-apple",
  "mac-intel": "blg-connector-macos-intel",
  windows: "blg-connector-windows-amd64.exe",
  "linux-amd64": "blg-connector-linux-amd64",
  "linux-arm64": "blg-connector-linux-arm64",
  "linux-arm": "blg-connector-linux-arm",
};

const RELEASE_BASE =
  "https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download";

export function assetFor(os: ConnectorOS): string {
  return ASSET[os];
}

export function downloadUrlFor(os: ConnectorOS): string {
  return `${RELEASE_BASE}/${assetFor(os)}`;
}

export function detectOS(
  nav: { platform?: string; userAgent?: string } = navigator,
): OSDetection {
  const p = (nav.platform || "").toLowerCase();
  const ua = (nav.userAgent || "").toLowerCase();
  if (p.includes("mac") || ua.includes("macintosh")) {
    // Apple Silicon reports as Intel in the browser — don't guess, ask.
    return { os: null, family: "mac", macNeedsChipChoice: true };
  }
  if (p.includes("win") || ua.includes("windows")) {
    return { os: "windows", family: "windows", macNeedsChipChoice: false };
  }
  if (p.includes("linux") || ua.includes("linux")) {
    return { os: "linux-amd64", family: "linux", macNeedsChipChoice: false };
  }
  return { os: null, family: null, macNeedsChipChoice: false };
}

export function buildConfigYaml(opts: {
  serverUrl: string;
  token: string;
  os: ConnectorOS;
  printer: PrinterChoice;
}): string {
  const testPath =
    opts.os === "windows" ? "file://C:/blg-wydruki" : "file:///tmp/blg-wydruki";
  const printer =
    opts.printer.mode === "ip"
      ? { name: "drukarka", host: opts.printer.ip, port: opts.printer.port ?? 9100 }
      : { name: "test-plik", host: testPath, port: 9100 };
  // JSON.stringify yields a valid double-quoted YAML scalar (quotes/backslashes
  // escaped), so a stray character in the user-typed printer IP can't produce a
  // malformed config.yaml.
  const q = (s: string) => JSON.stringify(s);
  return [
    `server_url: ${q(opts.serverUrl)}`,
    `token: ${q(opts.token)}`,
    "poll_interval_seconds: 5",
    "heartbeat_interval_seconds: 20",
    'listen: "127.0.0.1:9110"',
    "printers:",
    `  - name: ${q(printer.name)}`,
    `    host: ${q(printer.host)}`,
    `    port: ${printer.port}`,
    "",
  ].join("\n");
}

export function runCommandFor(os: ConnectorOS, asset: string): string {
  if (os === "windows") {
    return `cd $HOME\\Downloads; .\\${asset} -config config.yaml`;
  }
  if (os === "mac-apple" || os === "mac-intel") {
    return `cd ~/Downloads && xattr -d com.apple.quarantine ${asset} 2>/dev/null; chmod +x ${asset} && ./${asset} -config config.yaml`;
  }
  return `cd ~/Downloads && chmod +x ${asset} && ./${asset} -config config.yaml`;
}
