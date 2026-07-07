# F40 — One-File Installer + Wizard v2 — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** The connect-a-printer wizard produces ONE downloadable installer file per OS that sets the connector up as a background service (autostart, log-to-file, checksum-verified binary) — no terminal typing, no second file, and a printers step built on F39 discovery.

**Architecture:** Frontend-only. A new pure module `frontend/src/lib/installerSetup.ts` generates the full installer script text per OS family (mac `.command` / windows `.bat` / linux `.sh`) with the config.yaml embedded (reusing `buildConfigYaml`); `ConnectPrinterWizard.tsx` is reworked to: OS family (no chip question) → name → download ONE file + run instructions (Gatekeeper/SmartScreen guidance) → waiting → connected → printers step listing F39-discovered printers (advanced: IP → regenerate installer). Vitest is introduced for the generator's unit tests.

**Tech Stack:** React + TypeScript + i18next; Vitest (new devDep); bash / batch / PowerShell / launchd / schtasks / systemd --user inside the generated scripts.

## Global Constraints

- Frontend-only — NO backend or connector (Go) changes in this feature.
- The device token appears ONLY inside the downloaded file content (blob), never in a URL and never sent to any endpoint beyond what exists today.
- Generated scripts must be shell-safe: config content goes through a **quoted heredoc** (`<<'BLGCONF'`) on unix and **base64** on Windows — no direct interpolation of user-influenced strings into shell/batch syntax.
- Binary downloads come from `https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download/<asset>` and MUST be verified against the release's `SHA256SUMS`.
- Installers are idempotent: re-running stops the old instance, overwrites binary+config, restarts.
- Autostart: macOS LaunchAgent `uk.attv.blg-connector` (`RunAtLoad`+`KeepAlive`); Windows Task Scheduler task "BLG Connector" (ONLOGON, hidden window via a `.vbs`+`.cmd` pair to dodge schtasks' 261-char /TR limit and keep log redirection); Linux `systemd --user` `blg-connector.service` + `loginctl enable-linger`.
- All new UI strings in BOTH `frontend/src/i18n/locales/pl.json` and `en.json` (parity).
- Full gate on every task that touches frontend: `npm run format:check && npm run lint && npm run typecheck && npm run build` (plus `npm test` once vitest exists).
- Version at the end: app **v0.23.0** (minor). Commit convention `feat(wizard): …` etc. + footer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `installerSetup.ts` — pure installer generators + Vitest

**Files:**
- Create: `frontend/src/lib/installerSetup.ts`
- Create: `frontend/src/lib/installerSetup.test.ts`
- Modify: `frontend/package.json` (devDep `vitest`, script `"test": "vitest run"`)

**Interfaces:**
- Consumes: `buildConfigYaml`, `type PrinterChoice`, `type ConnectorOS` from `frontend/src/lib/connectorSetup.ts` (unchanged).
- Produces (used by Task 2):
  - `export type InstallerFamily = "mac" | "windows" | "linux"`
  - `export type InstallerOptions = { serverUrl: string; token: string; printer: PrinterChoice; virtualPrinter?: boolean }`
  - `export function installerFor(family: InstallerFamily, opts: InstallerOptions): { filename: string; content: string }`

- [ ] **Step 1: Vitest setup**

```bash
cd frontend && npm install -D vitest
```

Add to `package.json` scripts: `"test": "vitest run"`.

- [ ] **Step 2: Write the failing tests**

Create `frontend/src/lib/installerSetup.test.ts`:

```ts
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
    const decoded = new TextDecoder().decode(
      Uint8Array.from(atob(m![1]), (c) => c.charCodeAt(0)),
    );
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd frontend && npm test`
Expected: FAIL — module `./installerSetup` does not exist.

- [ ] **Step 4: Implement `installerSetup.ts`**

```ts
/**
 * F40: generate a single self-contained installer script per OS family.
 * Pure string builders — the wizard downloads the result as a blob. The
 * device token is embedded in the file (same trust level as config.yaml
 * today) and never leaves the browser any other way.
 */
import { type PrinterChoice, buildConfigYaml } from "./connectorSetup";

export type InstallerFamily = "mac" | "windows" | "linux";

export type InstallerOptions = {
  serverUrl: string;
  token: string;
  printer: PrinterChoice;
  virtualPrinter?: boolean;
};

const RELEASE_BASE = "https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download";

/** Representative ConnectorOS per family — buildConfigYaml only branches on
 *  windows vs unix (test-printer spool path). */
function configFor(family: InstallerFamily, opts: InstallerOptions): string {
  const os = family === "windows" ? "windows" : family === "mac" ? "mac-apple" : "linux-amd64";
  return buildConfigYaml({ serverUrl: opts.serverUrl, token: opts.token, os, printer: opts.printer });
}

/** UTF-8 → base64 (browser-safe). */
function toBase64(text: string): string {
  const bytes = new TextEncoder().encode(text);
  let bin = "";
  for (const b of bytes) bin += String.fromCharCode(b);
  return btoa(bin);
}

export function installerFor(
  family: InstallerFamily,
  opts: InstallerOptions,
): { filename: string; content: string } {
  if (family === "windows") return { filename: "Podlacz-BLG.bat", content: windowsBat(opts) };
  if (family === "mac") return { filename: "Podlacz-BLG.command", content: unixScript("mac", opts) };
  return { filename: "podlacz-blg.sh", content: unixScript("linux", opts) };
}

function unixScript(family: "mac" | "linux", opts: InstallerOptions): string {
  const cfg = configFor(family, opts);
  const isMac = family === "mac";
  const appDir = isMac ? '"$HOME/Library/Application Support/blg-connector"' : '"$HOME/.local/share/blg-connector"';
  const archCase = isMac
    ? `case "$(uname -m)" in
  arm64) ASSET="blg-connector-macos-apple" ;;
  *)     ASSET="blg-connector-macos-intel" ;;
esac`
    : `case "$(uname -m)" in
  x86_64)  ASSET="blg-connector-linux-amd64" ;;
  aarch64) ASSET="blg-connector-linux-arm64" ;;
  arm*)    ASSET="blg-connector-linux-arm" ;;
  *) echo "Nieobslugiwana architektura: $(uname -m)"; exit 1 ;;
esac`;
  const stopPrev = isMac
    ? 'launchctl unload "$PLIST" 2>/dev/null || true'
    : "systemctl --user stop blg-connector.service 2>/dev/null || true";
  const shaCheck = isMac ? "shasum -a 256 -c -" : "sha256sum -c -";
  const autostart = isMac
    ? `cat > "$PLIST" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>uk.attv.blg-connector</string>
  <key>ProgramArguments</key><array>
    <string>$APP_DIR/blg-connector</string>
    <string>-config</string>
    <string>$APP_DIR/config.yaml</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$APP_DIR/connector.log</string>
  <key>StandardErrorPath</key><string>$APP_DIR/connector.log</string>
</dict></plist>
PLIST
launchctl load "$PLIST"`
    : `mkdir -p "$HOME/.config/systemd/user"
cat > "$HOME/.config/systemd/user/blg-connector.service" <<UNIT
[Unit]
Description=BarcodeLabelGen connector

[Service]
ExecStart=$APP_DIR/blg-connector -config $APP_DIR/config.yaml
Restart=on-failure

[Install]
WantedBy=default.target
UNIT
systemctl --user daemon-reload
systemctl --user enable --now blg-connector.service
loginctl enable-linger "$USER" 2>/dev/null || true`;
  const restart = isMac
    ? 'launchctl unload "$PLIST" 2>/dev/null || true; launchctl load "$PLIST"'
    : "systemctl --user restart blg-connector.service";

  return `#!/bin/bash
# BarcodeLabelGen — instalator connectora (wygenerowany przez kreator).
# Uruchom ponownie w dowolnym momencie: aktualizuje program i konfiguracje.
# Flaga --virtual-printer: dodaje przechwytywanie wydrukow (wirtualna drukarka).
set -euo pipefail

APP_DIR=${appDir}
${isMac ? 'PLIST="$HOME/Library/LaunchAgents/uk.attv.blg-connector.plist"' : ""}
RELEASE_BASE="${RELEASE_BASE}"

${archCase}

echo "== BarcodeLabelGen: instaluje connector ($ASSET) =="
mkdir -p "$APP_DIR"
${isMac ? 'mkdir -p "$HOME/Library/LaunchAgents"' : ""}

${stopPrev}

cat > "$APP_DIR/config.yaml" <<'BLGCONF'
${cfg}BLGCONF

echo "-> pobieram program..."
curl -fsSL -o "$APP_DIR/blg-connector" "$RELEASE_BASE/$ASSET"
curl -fsSL -o "$APP_DIR/SHA256SUMS" "$RELEASE_BASE/SHA256SUMS"
echo "-> sprawdzam sume kontrolna..."
(cd "$APP_DIR" && grep " $ASSET\\$" SHA256SUMS | sed "s|$ASSET|blg-connector|" | ${shaCheck})
chmod +x "$APP_DIR/blg-connector"
${isMac ? 'xattr -d com.apple.quarantine "$APP_DIR/blg-connector" 2>/dev/null || true' : ""}

if [ "\${1:-}" = "--virtual-printer" ]; then
  if ! grep -q "^capture:" "$APP_DIR/config.yaml"; then
    printf 'capture:\\n  listen: "127.0.0.1:9101"\\n' >> "$APP_DIR/config.yaml"
  fi
  echo "-> tworze wirtualna drukarke (kolejka CUPS)..."
  lpadmin -p "BarcodeLabelGen-Capture" -E -v "socket://127.0.0.1:9101" -m raw || \\
    echo "UWAGA: lpadmin nie powiodl sie — uruchom z sudo albo dodaj sie do grupy lpadmin/_lpadmin."
fi

${autostart}

echo ""
echo "OK — gotowe! Connector dziala w tle i wstaje automatycznie po restarcie."
echo "Log: $APP_DIR/connector.log — mozesz wrocic do przegladarki."
`.replace(/\n{3,}/g, "\n\n");
}

function windowsBat(opts: InstallerOptions): string {
  const cfgB64 = toBase64(configFor("windows", opts));
  return `@echo off
setlocal
echo == BarcodeLabelGen: instaluje connector ==
set "APP=%LOCALAPPDATA%\\blg-connector"
mkdir "%APP%" 2>nul
set "ASSET=blg-connector-windows-amd64.exe"

rem Zatrzymaj poprzednia instancje (aktualizacja/naprawa)
taskkill /IM blg-connector.exe /F >nul 2>&1

rem Konfiguracja (base64 -> plik; omija problemy ze znakami specjalnymi)
powershell -NoProfile -Command "[IO.File]::WriteAllBytes('%APP%\\config.yaml',[Convert]::FromBase64String('${cfgB64}'))"

echo Pobieram program...
curl.exe -fsSL -o "%APP%\\blg-connector.exe" "${RELEASE_BASE}/%ASSET%"
curl.exe -fsSL -o "%APP%\\SHA256SUMS" "${RELEASE_BASE}/SHA256SUMS"
echo Sprawdzam sume kontrolna...
powershell -NoProfile -Command "$h=(Get-FileHash '%APP%\\blg-connector.exe' -Algorithm SHA256).Hash.ToLower(); $s=((Select-String -Path '%APP%\\SHA256SUMS' -Pattern [regex]::Escape('%ASSET%')).Line -split '\\s+')[0]; if($h -ne $s){exit 1}"
if errorlevel 1 (
  echo BLAD: suma kontrolna sie nie zgadza — sprobuj ponownie.
  pause
  exit /b 1
)

rem Pomocnicze pliki: log + ukryte okno
> "%APP%\\run-blg.cmd" echo @"%APP%\\blg-connector.exe" -config "%APP%\\config.yaml" ^>^> "%APP%\\connector.log" 2^>^&1
> "%APP%\\run-blg.vbs" echo CreateObject("Wscript.Shell").Run """%APP%\\run-blg.cmd""", 0, False

rem Autostart przy logowaniu + start teraz (bez okna)
schtasks /Create /F /TN "BLG Connector" /SC ONLOGON /TR "wscript \\"%APP%\\run-blg.vbs\\"" >nul
schtasks /Run /TN "BLG Connector" >nul

echo.
echo OK — gotowe! Connector dziala w tle i wstaje automatycznie po zalogowaniu.
echo Log: %APP%\\connector.log — mozesz wrocic do przegladarki.
pause
`;
}
```

Implementation notes for the engineer:
- The template literals above are the INTENT; when transcribing, be careful with escaping levels (TS template literal vs generated bash). Verify by running the tests, and additionally print one generated mac script to a temp file and run `bash -n` on it (syntax check) — add that as a manual sanity step, not a unit test.
- `buildConfigYaml` output already ends with `\n`, so `${cfg}BLGCONF` puts the delimiter on its own line.
- Diacritic-free Polish in generated scripts is deliberate (batch/cmd codepage safety).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npm test`
Expected: 5 tests PASS. Also `bash -n` sanity on a dumped mac + linux script (node -e snippet writing installerFor output to /tmp, then `bash -n`).

- [ ] **Step 6: Gate + commit**

Run: `npm run format:check && npm run lint && npm run typecheck && npm run build && npm test`

```bash
git add frontend/src/lib/installerSetup.ts frontend/src/lib/installerSetup.test.ts frontend/package.json frontend/package-lock.json
git commit -m "feat(wizard): one-file installer generators (mac/windows/linux) + vitest (F40)"
```

---

### Task 2: Wizard v2 — rework `ConnectPrinterWizard` around the installer

**Files:**
- Modify: `frontend/src/pages/ConnectPrinterWizard.tsx` (major rework)
- Modify: `frontend/src/lib/connectorSetup.ts` (drop now-unused exports)
- Modify: `frontend/src/i18n/locales/pl.json`, `en.json`
- Test: covered by Task 1's unit tests + full gate (no component test framework in repo)

**Interfaces:**
- Consumes: `installerFor`, `InstallerFamily` (Task 1); existing `useCreateDevice`, `useDeviceOnline`, `useDevices` (`frontend/src/hooks/useDevices.ts`); `DevicePrinter.kind` (F39).
- Produces: UI only.

- [ ] **Step 1: New step flow**

`type Step = "os" | "name" | "install" | "waiting" | "success" | "printers" | "virtual"`.

Changes vs today:
1. **os**: three tiles only (Mac 🍎 / Windows 🪟 / Linux 🐧) mapped to `InstallerFamily`; auto-detected family pre-highlighted (`detectOS().family`); REMOVE the mac chip sub-choice and the linux-arm tile (arch is autodetected by the installer).
2. **name**: unchanged, but on success go to `"install"`.
3. **install** (replaces `download`+`run`): ONE primary button „Pobierz instalator" → `download(filename, content)` using `installerFor(family, { serverUrl, token: created.token, printer: {mode:"test"} })`. Below it, per-family run instructions:
   - mac: „Otwórz Pobrane → kliknij plik PRAWYM przyciskiem → Otwórz → Otwórz. (macOS pokaże ostrzeżenie — to normalne: plik nie jest jeszcze podpisany cyfrowo.)"
   - windows: „Uruchom pobrany plik. Gdy pojawi się niebieskie okno SmartScreen: Więcej informacji → Uruchom mimo to."
   - linux: „W terminalu: `bash ~/Pobrane/podlacz-blg.sh` (jedyna komenda — instalator zrobi resztę)."
   Keep the token-privacy note. „Dalej" → `"waiting"`.
4. **waiting/success**: unchanged logic; success gains two buttons: „Drukarki →" (`"printers"`) and „Zakończ".
5. **printers** (replaces old `printer`): while active, poll `useDevices()` (see Step 2) and show `created.device`'s current `printers` list — each row: name + badge for `kind === "local"` („z tego komputera"). Empty state: „Nie widzę jeszcze drukarek — podłącz drukarkę USB i dodaj ją w ustawieniach systemu, odświeżę listę sam." Collapsible „Zaawansowane: drukarka sieciowa (IP)": IP input → button „Pobierz instalator z tą drukarką" → `installerFor(family, { …, printer: { mode: "ip", ip } })` + hint „uruchom go ponownie — zaktualizuje konfigurację". Secondary link → `"virtual"`. Primary „Zakończ".
6. **virtual**: one screen. mac/linux: copyable command `bash ~/Pobrane/Podlacz-BLG.command --virtual-printer` (linux: `bash ~/Pobrane/podlacz-blg.sh --virtual-printer`) + one-line explanation (drukuj z innych programów → wydruki lądują w Inbox). windows: 4-step ZDesigner guide (driver from zebra.com; add printer: port Standard TCP/IP 127.0.0.1:9101, RAW, SNMP off; print from any app → Inbox). Back → `"printers"`.

- [ ] **Step 2: Polling the device's printers on the printers step**

In the wizard component (no new hook file needed):

```ts
const devices = useDevices();
useEffect(() => {
  if (step !== "printers") return;
  const h = setInterval(() => void devices.refetch(), 5000);
  return () => clearInterval(h);
}, [step, devices]);
const livePrinters =
  devices.data?.find((d) => d.id === created?.device.id)?.printers ?? [];
```

(Adapt to `useDevices`' actual return shape — check the hook first.)

- [ ] **Step 3: connectorSetup.ts cleanup**

Remove now-unused exports `assetFor`, `downloadUrlFor`, `runCommandFor` and the `ASSET`/`RELEASE_BASE` consts IF no other module imports them (grep first; `installerSetup.ts` has its own RELEASE_BASE). Keep `detectOS`, `buildConfigYaml`, types. Update the module doc comment.

- [ ] **Step 4: i18n**

Replace obsolete wizard keys (dlProgram, dlConfig, dlConfigSub, runTitle, runHint, keepOpen, printerRedownload, downloadNewConfig, linuxArm, macChip, macApple, macIntel — remove) and add new ones (installTitle, installHint, installDownload, installRun.mac/.windows/.linux, unsignedNote, printersTitle, printersHint, printersEmpty, printersLocalBadge, advancedIp, downloadWithPrinter, rerunHint, virtualLink, virtualTitle, virtualHintUnix, virtualCmd, virtualWinStep1-4, finish) — exact strings PL first, EN mirrored, keep parity. Keep existing keys still used (osQuestion, nameQuestion, waiting*, connected*, tip1-3, tokenPrivacy, …).

- [ ] **Step 5: Gate**

Run: `cd frontend && npm run format:check && npm run lint && npm run typecheck && npm run build && npm test`
Expected: all green. Manually grep both locale files for parity of every `wizard.*` key (same key set).

- [ ] **Step 6: Commit**

```bash
git add frontend/src/pages/ConnectPrinterWizard.tsx frontend/src/lib/connectorSetup.ts frontend/src/i18n/locales/pl.json frontend/src/i18n/locales/en.json
git commit -m "feat(wizard): v2 — one-file installer flow, discovered-printers step, virtual-printer guide (F40)"
```

---

### Task 3: CI test step + docs

**Files:**
- Modify: `.github/workflows/ci.yml` (frontend job: add Vitest step after typecheck)
- Modify: `connector/README.md` (point the manual-install docs at the wizard as the primary path; manual stays as advanced)

**Interfaces:** none new.

- [ ] **Step 1: ci.yml**

After the "TypeScript typecheck" step add:

```yaml
      - name: Vitest
        run: npm test
```

- [ ] **Step 2: connector/README.md**

At the top of the setup section add one Polish paragraph: „**Najprostsza droga:** strona *Urządzenia* → „Podłącz drukarkę" generuje jednoplikowy instalator (macOS/Windows/Linux), który konfiguruje wszystko sam — łącznie z autostartem i pracą w tle. Poniższa instrukcja ręczna pozostaje dla zaawansowanych."

- [ ] **Step 3: Verify + commit**

`python3 -c "import yaml; yaml.safe_load(open('.github/workflows/ci.yml'))"` → OK.

```bash
git add .github/workflows/ci.yml connector/README.md
git commit -m "chore(ci): run vitest in frontend job; docs: wizard-first install path (F40)"
```

---

### Task 4: Release v0.23.0

**Files:**
- Modify: `CHANGELOG.md`, `backend/app/version.py`, `backend/pyproject.toml`, `frontend/package.json` (+ `backend/uv.lock` via `uv lock`)

- [ ] **Step 1: bumps + changelog**

Versions → `0.23.0` (all three + uv lock). CHANGELOG: new `## [0.23.0] — <date>` `### Added` describing F40 (one-file installer per OS, checksum-verified download, background service + autostart via LaunchAgent/Task Scheduler/systemd, wizard v2 with discovered-printers step and virtual-printer guide, no more two-file download/terminal commands) + `### Changed` (wizard flow replaces manual binary+config download). Link refs updated.

- [ ] **Step 2: Full verification**

```bash
cd backend && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
cd ../frontend && npm run format:check && npm run lint && npm run typecheck && npm run build && npm test
```

(Connector untouched — no Go gate needed; CI will run it anyway.)

- [ ] **Step 3: Commit**

```bash
git add -A
git commit -m "chore(release): v0.23.0 — one-file connector installer + wizard v2 (F40)"
```

Tag + push + GitHub release are done by the controller after the final whole-branch review (release.yml auto-attaches connector binaries; they're unchanged but `latest` must keep carrying them — it will, workflow rebuilds from the tag).

- [ ] **Step 4: Post-release (controller): rebuild dev instance + user E2E**

Rebuild linuxserv1 (`docker compose up -d --build web nginx`), verify `/api/health` → 0.23.0, then user checkpoint: run the wizard on their Mac, download ONE file, right-click→Open, watch it connect, see ZD421 in the printers step.
