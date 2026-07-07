import { describe, expect, it } from "vitest";
import { installerFor } from "./installerSetup";

const OPTS = {
  serverUrl: "https://linuxserv1.tailc29352.ts.net:18003",
  token: "blg_abc123",
  printer: { mode: "test" } as const,
};

describe("installerFor", () => {
  it("mac: .command with arch autodetect, checksum, LaunchAgent, quarantine strip", () => {
    const { filename, content } = installerFor("mac", OPTS);
    expect(filename).toBe("Podlacz-BLG.command");
    expect(content.startsWith("#!/bin/bash")).toBe(true);
    expect(content).toContain('case "$(uname -m)"');
    expect(content).toContain("blg-connector-macos-apple");
    expect(content).toContain("blg-connector-macos-intel");
    expect(content).toContain("shasum -a 256 -c");
    expect(content).toContain("uk.attv.blg-connector.plist");
    expect(content).toContain("xattr -d com.apple.quarantine");
    // config embedded via quoted heredoc, token inside it
    expect(content).toContain("<<'BLGCONF'");
    expect(content).toContain('token: "blg_abc123"');
    // idempotency: stops previous instance
    expect(content).toContain("launchctl unload");
    // mac logs to a plain file, not journald
    expect(content).toContain("Log: $APP_DIR/connector.log");
  });

  it("linux: .sh with three arch cases, systemd --user, linger", () => {
    const { filename, content } = installerFor("linux", OPTS);
    expect(filename).toBe("podlacz-blg.sh");
    expect(content).toContain("blg-connector-linux-amd64");
    expect(content).toContain("blg-connector-linux-arm64");
    expect(content).toContain("blg-connector-linux-arm");
    expect(content).toContain("sha256sum -c");
    expect(content).toContain("systemctl --user enable --now blg-connector.service");
    expect(content).toContain("loginctl enable-linger");
    expect(content).toContain("<<'BLGCONF'");
    // systemd logs to journald, not a flat file — the final message must say so
    expect(content).toContain("Log: journalctl --user -u blg-connector.service");
    expect(content).not.toContain("Log: $APP_DIR/connector.log");
  });

  it("windows: .bat with base64 config (decodes to the YAML), checksum, schtasks + vbs", () => {
    const { filename, content } = installerFor("windows", OPTS);
    expect(filename).toBe("Podlacz-BLG.bat");
    expect(content).toContain("blg-connector-windows-amd64.exe");
    expect(content).toContain("Get-FileHash");
    expect(content).toContain('schtasks /Create /F /TN "BLG Connector"');
    expect(content).toContain("run-blg.vbs");
    const m = content.match(/FromBase64String\('([^']+)'\)/);
    expect(m).not.toBeNull();
    const decoded = new TextDecoder().decode(Uint8Array.from(atob(m![1]), (c) => c.charCodeAt(0)));
    expect(decoded).toContain('token: "blg_abc123"');
    expect(decoded).toContain('server_url: "https://linuxserv1.tailc29352.ts.net:18003"');
  });

  it("windows: checksum comparison uses -SimpleMatch, not a broken -Pattern expression", () => {
    const { content } = installerFor("windows", OPTS);
    expect(content).toContain("-SimpleMatch '%ASSET%'");
    expect(content).not.toContain("[regex]::Escape");
    expect(content).not.toContain("-Pattern [regex]");
  });

  it("windows: schtasks /Create failure aborts with guidance, /Run failure only warns", () => {
    const { content } = installerFor("windows", OPTS);
    const createIdx = content.indexOf('schtasks /Create /F /TN "BLG Connector"');
    const runIdx = content.indexOf('schtasks /Run /TN "BLG Connector"');
    expect(createIdx).toBeGreaterThan(-1);
    expect(runIdx).toBeGreaterThan(createIdx);
    const betweenCreateAndRun = content.slice(createIdx, runIdx);
    expect(betweenCreateAndRun).toContain("if errorlevel 1");
    expect(betweenCreateAndRun).toContain("exit /b 1");
    expect(betweenCreateAndRun).toContain("administrator");
    const afterRun = content.slice(runIdx);
    const afterRunBlock = afterRun.split(/\r?\n\r?\n/)[0];
    expect(afterRunBlock).toContain("if errorlevel 1");
    expect(afterRunBlock).not.toContain("exit /b 1");
  });

  it("windows: both curl.exe downloads are checked for failure", () => {
    const { content } = installerFor("windows", OPTS);
    const curlLines = content
      .split("\n")
      .map((line, i) => ({ line, i }))
      .filter(({ line }) => line.trim().startsWith("curl.exe"));
    expect(curlLines).toHaveLength(2);
    const lines = content.split("\n");
    for (const { i } of curlLines) {
      const nextNonEmpty = lines.slice(i + 1).find((l) => l.trim() !== "");
      expect(nextNonEmpty).toContain("if errorlevel 1");
      expect(nextNonEmpty).toMatch(/pobieranie nie powiodl/i);
    }
  });

  it("windows: generated text has no non-ASCII em-dashes (cp852 mojibake)", () => {
    const { content } = installerFor("windows", OPTS);
    expect(content).not.toMatch(/[–—]/);
  });

  it("unix: --virtual-printer support appends capture + lpadmin", () => {
    const { content } = installerFor("mac", OPTS);
    expect(content).toContain("--virtual-printer");
    expect(content).toContain("127.0.0.1:9101");
    expect(content).toContain("lpadmin");
  });

  it("unix: capture section is preserved on re-run even without the flag", () => {
    const { content } = installerFor("linux", OPTS);
    expect(content).toContain("HAD_CAPTURE");
    expect(content).toContain('grep -q "^capture:" "$APP_DIR/config.yaml"');
    expect(content).toContain('if [ "${1:-}" = "--virtual-printer" ] || [ "$HAD_CAPTURE" = "1" ]');
  });

  it("unix: lpadmin (queue creation) only runs when --virtual-printer is explicitly passed", () => {
    const { content } = installerFor("linux", OPTS);
    const condIdx = content.indexOf(
      'if [ "${1:-}" = "--virtual-printer" ] || [ "$HAD_CAPTURE" = "1" ]',
    );
    expect(condIdx).toBeGreaterThan(-1);
    const fiIdx = content.indexOf("\nfi", condIdx);
    const block = content.slice(condIdx, fiIdx);
    // lpadmin must be nested under its own flag-only check inside the outer block
    expect(block).toContain('if [ "${1:-}" = "--virtual-printer" ]; then');
    expect(block).toContain("lpadmin");
  });

  it("hostile printer IP cannot escape the heredoc", () => {
    const { content } = installerFor("linux", {
      ...OPTS,
      printer: { mode: "ip", ip: '1.2.3.4"\nBLGCONF\n$(rm -rf ~)' },
    });
    const afterMarker = content.split("<<'BLGCONF'")[1];
    const body = afterMarker.slice(0, afterMarker.indexOf("\nBLGCONF\n"));
    // JSON-escaped by buildConfigYaml: stays on one line inside the heredoc
    expect(body).toContain("\\n");
    expect(body.split("\n").some((l) => l.trim() === "BLGCONF")).toBe(false);
  });
});
