/**
 * Pure helpers shared by the "Connect a printer" wizard (F38/F40): detect the
 * user's OS/family and build a ready-to-embed config.yaml. No React, no I/O.
 * The per-OS installer script/binary naming and download commands now live in
 * `installerSetup.ts` (F40's one-file installer) — this module only keeps the
 * pieces still shared with it (`buildConfigYaml`, the `PrinterChoice` type)
 * plus OS auto-detection for the wizard's first step.
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

export function detectOS(nav: { platform?: string; userAgent?: string } = navigator): OSDetection {
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
  const testPath = opts.os === "windows" ? "file://C:/blg-wydruki" : "file:///tmp/blg-wydruki";
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
