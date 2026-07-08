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
    expect(filename).toBe("BLG-Connect.command");
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
    expect(filename).toBe("blg-connect.sh");
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

  it("windows: .bat with base64 config (decodes to the YAML), checksum, HKCU Run + vbs autostart", () => {
    const { filename, content } = installerFor("windows", OPTS);
    expect(filename).toBe("BLG-Connect.bat");
    expect(content).toContain("blg-connector-windows-amd64.exe");
    expect(content).toContain("Get-FileHash");
    expect(content).toContain('reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"');
    expect(content).not.toContain("schtasks");
    expect(content).toContain("run-blg.vbs");
    const m = content.match(/FromBase64String\('([^']+)'\)/);
    expect(m).not.toBeNull();
    const decoded = new TextDecoder().decode(Uint8Array.from(atob(m![1]), (c) => c.charCodeAt(0)));
    expect(decoded).toContain('token: "blg_abc123"');
    expect(decoded).toContain('server_url: "https://linuxserv1.tailc29352.ts.net:18003"');
  });

  it("windows: config always includes a capture section (ZDesigner virtual-printer guide targets port 9101)", () => {
    const { content } = installerFor("windows", OPTS);
    const m = content.match(/FromBase64String\('([^']+)'\)/);
    expect(m).not.toBeNull();
    const decoded = new TextDecoder().decode(Uint8Array.from(atob(m![1]), (c) => c.charCodeAt(0)));
    expect(decoded).toContain("capture:");
    expect(decoded).toContain("127.0.0.1:9101");
  });

  it("windows: generates CRLF line endings throughout", () => {
    const { content } = installerFor("windows", OPTS);
    expect(content).toContain("\r\n");
    expect(content.split("\r\n").every((l) => !l.includes("\n"))).toBe(true);
  });

  it("windows: checksum comparison uses -SimpleMatch, not a broken -Pattern expression", () => {
    const { content } = installerFor("windows", OPTS);
    expect(content).toContain("-SimpleMatch '%ASSET%'");
    expect(content).not.toContain("[regex]::Escape");
    expect(content).not.toContain("-Pattern [regex]");
  });

  it("windows: HKCU Run key add is elevation-free (no schtasks/admin) and aborts on failure", () => {
    const { content } = installerFor("windows", OPTS);
    const regIdx = content.indexOf(
      'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"',
    );
    expect(regIdx).toBeGreaterThan(-1);
    expect(content).not.toContain("schtasks");
    const afterReg = content.slice(regIdx);
    const block = afterReg.split(/\r\n\r\n/)[0];
    expect(block).toContain("if errorlevel 1");
    expect(block).toContain("exit /b 1");
  });

  it("windows: starts the connector immediately via wscript, after the autostart key is registered", () => {
    const { content } = installerFor("windows", OPTS);
    const regIdx = content.indexOf(
      'reg add "HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run"',
    );
    const startNowIdx = content.indexOf('wscript "%APP%\\run-blg.vbs"');
    expect(regIdx).toBeGreaterThan(-1);
    expect(startNowIdx).toBeGreaterThan(regIdx);
  });

  it("windows: config-write PowerShell command is checked for failure", () => {
    const { content } = installerFor("windows", OPTS);
    const writeIdx = content.indexOf("WriteAllBytes");
    expect(writeIdx).toBeGreaterThan(-1);
    const after = content.slice(writeIdx);
    const nextLine = after.split(/\r\n/)[1];
    expect(nextLine).toContain("if errorlevel 1");
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

describe("installerArtifact", () => {
  it("mac artifact is a zip carrying the exec bit", async () => {
    const { installerArtifact } = await import("./installerSetup");
    const { filename, blob } = installerArtifact("mac", OPTS);
    expect(filename).toBe("BLG-Connect.zip");
    const bytes = new Uint8Array(await blob.arrayBuffer());
    expect([bytes[0], bytes[1], bytes[2], bytes[3]]).toEqual([0x50, 0x4b, 0x03, 0x04]);
    const text = new TextDecoder().decode(bytes);
    expect(text).toContain("BLG-Connect.command");
    // stored (no compression) => the script is plaintext inside the zip
    expect(text).toContain('token: "blg_abc123"');
    let idx = -1;
    for (let i = 0; i < bytes.length - 4; i++) {
      if (
        bytes[i] === 0x50 &&
        bytes[i + 1] === 0x4b &&
        bytes[i + 2] === 0x01 &&
        bytes[i + 3] === 0x02
      ) {
        idx = i;
        break;
      }
    }
    expect(idx).toBeGreaterThan(-1);
    const ext =
      (bytes[idx + 38] |
        (bytes[idx + 39] << 8) |
        (bytes[idx + 40] << 16) |
        (bytes[idx + 41] << 24)) >>>
      0;
    expect((ext >>> 16) & 0o7777).toBe(0o755);
  });

  it("windows and linux artifacts are plain text with new names", async () => {
    const { installerArtifact } = await import("./installerSetup");
    const w = installerArtifact("windows", OPTS);
    expect(w.filename).toBe("BLG-Connect.bat");
    expect(await w.blob.text()).toContain("blg-connector-windows-amd64.exe");
    const l = installerArtifact("linux", OPTS);
    expect(l.filename).toBe("blg-connect.sh");
  });

  it("installers self-verify the connection (step 3 status poll)", () => {
    expect(installerFor("mac", OPTS).content).toContain("9110/status");
    expect(installerFor("linux", OPTS).content).toContain("[3/3]");
    expect(installerFor("windows", OPTS).content).toContain("9110/status");
  });
});
