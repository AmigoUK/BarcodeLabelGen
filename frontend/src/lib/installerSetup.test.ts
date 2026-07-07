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

  it("unix: --virtual-printer support appends capture + lpadmin", () => {
    const { content } = installerFor("mac", OPTS);
    expect(content).toContain("--virtual-printer");
    expect(content).toContain("127.0.0.1:9101");
    expect(content).toContain("lpadmin");
  });

  it("config heredoc cannot be broken by its own delimiter", () => {
    const { content } = installerFor("linux", OPTS);
    const body = content.split("<<'BLGCONF'")[1].split("\nBLGCONF")[0];
    expect(body).not.toContain("\nBLGCONF\n");
  });
});
