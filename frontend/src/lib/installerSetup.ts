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
  return buildConfigYaml({
    serverUrl: opts.serverUrl,
    token: opts.token,
    os,
    printer: opts.printer,
  });
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
  if (family === "mac")
    return { filename: "Podlacz-BLG.command", content: unixScript("mac", opts) };
  return { filename: "podlacz-blg.sh", content: unixScript("linux", opts) };
}

function unixScript(family: "mac" | "linux", opts: InstallerOptions): string {
  const cfg = configFor(family, opts);
  const isMac = family === "mac";
  const appDir = isMac
    ? '"$HOME/Library/Application Support/blg-connector"'
    : '"$HOME/.local/share/blg-connector"';
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

  const logLine = isMac
    ? 'echo "Log: $APP_DIR/connector.log — mozesz wrocic do przegladarki."'
    : 'echo "Log: journalctl --user -u blg-connector.service — mozesz wrocic do przegladarki."';

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

HAD_CAPTURE=0
grep -q "^capture:" "$APP_DIR/config.yaml" 2>/dev/null && HAD_CAPTURE=1

cat > "$APP_DIR/config.yaml" <<'BLGCONF'
${cfg}BLGCONF

echo "-> pobieram program..."
curl -fsSL -o "$APP_DIR/blg-connector" "$RELEASE_BASE/$ASSET"
curl -fsSL -o "$APP_DIR/SHA256SUMS" "$RELEASE_BASE/SHA256SUMS"
echo "-> sprawdzam sume kontrolna..."
(cd "$APP_DIR" && grep " $ASSET\\$" SHA256SUMS | sed "s|$ASSET|blg-connector|" | ${shaCheck})
chmod +x "$APP_DIR/blg-connector"
${isMac ? 'xattr -d com.apple.quarantine "$APP_DIR/blg-connector" 2>/dev/null || true' : ""}

if [ "\${1:-}" = "--virtual-printer" ] || [ "$HAD_CAPTURE" = "1" ]; then
  if ! grep -q "^capture:" "$APP_DIR/config.yaml"; then
    printf 'capture:\\n  listen: "127.0.0.1:9101"\\n' >> "$APP_DIR/config.yaml"
  fi
  if [ "\${1:-}" = "--virtual-printer" ]; then
    echo "-> tworze wirtualna drukarke (kolejka CUPS)..."
    lpadmin -p "BarcodeLabelGen-Capture" -E -v "socket://127.0.0.1:9101" -m raw || \\
      echo "UWAGA: lpadmin nie powiodl sie — uruchom z sudo albo dodaj sie do grupy lpadmin/_lpadmin."
  fi
fi

${autostart}

echo ""
echo "OK — gotowe! Connector dziala w tle i wstaje automatycznie po restarcie."
${logLine}
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
if errorlevel 1 (echo BLAD: pobieranie nie powiodlo sie - sprawdz internet. & pause & exit /b 1)
curl.exe -fsSL -o "%APP%\\SHA256SUMS" "${RELEASE_BASE}/SHA256SUMS"
if errorlevel 1 (echo BLAD: pobieranie nie powiodlo sie - sprawdz internet. & pause & exit /b 1)
echo Sprawdzam sume kontrolna...
powershell -NoProfile -Command "$h=(Get-FileHash '%APP%\\blg-connector.exe' -Algorithm SHA256).Hash.ToLower(); $s=((Select-String -Path '%APP%\\SHA256SUMS' -SimpleMatch '%ASSET%').Line -split '\\s+')[0]; if($h -ne $s){exit 1}"
if errorlevel 1 (
  echo BLAD: suma kontrolna sie nie zgadza - sprobuj ponownie.
  pause
  exit /b 1
)

rem Pomocnicze pliki: log + ukryte okno
> "%APP%\\run-blg.cmd" echo @"%APP%\\blg-connector.exe" -config "%APP%\\config.yaml" ^>^> "%APP%\\connector.log" 2^>^&1
> "%APP%\\run-blg.vbs" echo CreateObject("Wscript.Shell").Run """%APP%\\run-blg.cmd""", 0, False

rem Autostart przy logowaniu + start teraz (bez okna)
schtasks /Create /F /TN "BLG Connector" /SC ONLOGON /TR "wscript \\"%APP%\\run-blg.vbs\\"" >nul
if errorlevel 1 (
  echo BLAD: nie udalo sie dodac autostartu. Uruchom ten plik jako administrator
  echo (prawy przycisk - Uruchom jako administrator).
  pause
  exit /b 1
)
schtasks /Run /TN "BLG Connector" >nul
if errorlevel 1 (
  echo UWAGA: nie udalo sie uruchomic uslugi teraz - zaloguj sie ponownie, aby ja uruchomic.
)

echo.
echo OK - gotowe! Connector dziala w tle i wstaje automatycznie po zalogowaniu.
echo Log: %APP%\\connector.log - mozesz wrocic do przegladarki.
pause
`;
}
