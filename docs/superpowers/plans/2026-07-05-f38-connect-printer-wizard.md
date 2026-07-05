# F38 — Connect-a-printer Wizard Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A guided, non-technical in-app wizard on the Devices page that takes a user from zero to a connected connector — auto-detecting their OS, creating the device+token, generating a ready-to-run `config.yaml` (no editing), giving one copy-paste run command, and detecting the connection live.

**Architecture:** Frontend-only. A pure helper module `lib/connectorSetup.ts` builds the config/asset/command strings; a multi-step modal `ConnectPrinterWizard.tsx` drives the flow reusing `useCreateDevice`/`useDevices`; a small polling hook flips the wizard to "connected". No backend or connector code changes. The release process is extended to attach all six connector binaries so `releases/latest/download/<asset>` links always resolve.

**Tech Stack:** React 18 + TypeScript + react-query + react-i18next (frontend gate: `npm run typecheck` + `npm run lint`; no unit-test framework by project convention — behaviour is verified end-to-end live by the controller).

## Global Constraints

- Spec: `docs/superpowers/specs/2026-07-05-f38-connect-printer-wizard-design.md`. Variant A, frontend-only.
- **No backend or connector (`connector/`, `backend/`) code changes.** Reuse `POST /api/devices` (`useCreateDevice` → `{device, token}`) and `GET /api/devices` (`useDevices` → `Device[]`).
- `config.yaml` is built in the browser: `server_url` = `window.location.origin`; `token` from the create response; **token never appears in a URL**, only in the downloaded file.
- Test-printer mode is the DEFAULT; the real printer IP is a SEPARATE step after the success screen.
- Online threshold mirrors the app: a device is online if `last_seen_at` is within `60_000` ms (`ONLINE_WINDOW_MS`, as in `DevicesPage.tsx`/`PrintModal.tsx`).
- Download links point to `https://github.com/AmigoUK/BarcodeLabelGen/releases/latest/download/<asset>`; the release MUST carry all six connector binaries.
- Version bump app `0.20.1 → 0.21.0` across all THREE sources (`frontend/package.json`, `backend/pyproject.toml`, `backend/app/version.py`) — `backend/tests/test_version_sync.py` enforces the backend two.
- Polish + English i18n parity. Commit trailer `Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>`.

---

### Task 1: `lib/connectorSetup.ts` — pure setup logic

**Files:**
- Create: `frontend/src/lib/connectorSetup.ts`

**Interfaces:**
- Consumes: nothing.
- Produces:
  - `type ConnectorOS = "mac-apple" | "mac-intel" | "windows" | "linux-amd64" | "linux-arm64" | "linux-arm"`
  - `type OSDetection = { os: ConnectorOS | null; family: "mac" | "windows" | "linux" | null; macNeedsChipChoice: boolean }`
  - `type PrinterChoice = { mode: "test" } | { mode: "ip"; ip: string; port?: number }`
  - `function detectOS(nav?: { platform?: string; userAgent?: string }): OSDetection`
  - `function assetFor(os: ConnectorOS): string`
  - `function downloadUrlFor(os: ConnectorOS): string`
  - `function buildConfigYaml(opts: { serverUrl: string; token: string; os: ConnectorOS; printer: PrinterChoice }): string`
  - `function runCommandFor(os: ConnectorOS, asset: string): string`
  Task 2 (wizard) imports all of these.

- [ ] **Step 1: Write `frontend/src/lib/connectorSetup.ts`**

```ts
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
  return [
    `server_url: "${opts.serverUrl}"`,
    `token: "${opts.token}"`,
    "poll_interval_seconds: 5",
    "heartbeat_interval_seconds: 20",
    'listen: "127.0.0.1:9110"',
    "printers:",
    `  - name: "${printer.name}"`,
    `    host: "${printer.host}"`,
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
```

- [ ] **Step 2: Typecheck + lint**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/frontend
npm run typecheck && npm run lint
```
Expected: both clean.

- [ ] **Step 3: Sanity-check the pure outputs (no test runner — inspect by eval)**

Run (uses the TypeScript compiler's transpile via a throwaway node check — confirms the strings, not just types):
```bash
cd /var/www/html/BarcodeLabelGen/frontend
npx tsx -e 'import {buildConfigYaml,runCommandFor,downloadUrlFor,detectOS} from "./src/lib/connectorSetup.ts"; console.log(downloadUrlFor("mac-intel")); console.log(runCommandFor("mac-intel","blg-connector-macos-intel")); console.log(buildConfigYaml({serverUrl:"https://x.ts.net:18003",token:"blg_abc",os:"mac-intel",printer:{mode:"test"}})); console.log(JSON.stringify(detectOS({platform:"MacIntel"})));' 2>/dev/null || echo "tsx not available — skip, rely on live verification"
```
Expected (if `tsx` present): the download URL ends `/blg-connector-macos-intel`; the command contains `xattr -d com.apple.quarantine`; the YAML starts `server_url: "https://x.ts.net:18003"` and contains `host: "file:///tmp/blg-wydruki"`; detection returns `macNeedsChipChoice:true`. If `tsx` is absent, that's fine — behaviour is verified end-to-end live.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add frontend/src/lib/connectorSetup.ts
git commit -m "feat(wizard): connectorSetup helpers — OS detect, config, run command (F38)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 2: `ConnectPrinterWizard` component + online-poll hook

**Files:**
- Create: `frontend/src/editor/ConnectPrinterWizard.tsx` (placed under `editor/`? No — devices UI. Use `frontend/src/pages/ConnectPrinterWizard.tsx`)
- Modify: `frontend/src/hooks/useDevices.ts` (add `useDeviceOnline`)

Correction — create at: `frontend/src/pages/ConnectPrinterWizard.tsx`.

**Interfaces:**
- Consumes: `detectOS`, `assetFor`, `downloadUrlFor`, `buildConfigYaml`, `runCommandFor`, `ConnectorOS`, `PrinterChoice` (Task 1); `useCreateDevice` and the new `useDeviceOnline` (this task); `Modal`, `Button`, `Input`, `Select` from `components/ui`; `useTranslation`.
- Produces:
  - `useDevices.ts`: `function useDeviceOnline(deviceId: number | null, enabled: boolean)` — react-query hook polling `/api/devices` every 3s while enabled, `select` → `boolean` (that device online within 60s).
  - `ConnectPrinterWizard.tsx`: `export function ConnectPrinterWizard({ open, onClose }: { open: boolean; onClose: () => void })`.
  Task 3 mounts `<ConnectPrinterWizard>`.

- [ ] **Step 1: Add `useDeviceOnline` to `frontend/src/hooks/useDevices.ts`**

Add these imports at the top if missing (`useQuery` is already imported) and append the hook:

```ts
// Polls the devices list fast (every 3s) while the connect wizard waits for a
// specific device to come online. Mirrors the 60s window used elsewhere.
export function useDeviceOnline(deviceId: number | null, enabled: boolean) {
  return useQuery({
    queryKey: ["device-online", deviceId] as const,
    queryFn: () => api<{ devices: Device[] }>("/api/devices").then((r) => r.devices),
    enabled: enabled && deviceId != null,
    refetchInterval: enabled ? 3000 : false,
    select: (devices: Device[]) => {
      const d = devices.find((x) => x.id === deviceId);
      if (!d?.last_seen_at) return false;
      return Date.now() - new Date(d.last_seen_at).getTime() < 60_000;
    },
  });
}
```

- [ ] **Step 2: Write `frontend/src/pages/ConnectPrinterWizard.tsx`**

```tsx
/**
 * F38 — "Connect a printer" wizard. Guides a non-technical user from zero to a
 * connected connector: detect OS → name the computer (creates device+token) →
 * download the binary + a ready config.yaml → run one command → live "connected"
 * detection → optional real printer. No manual file editing anywhere.
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { useCreateDevice, useDeviceOnline } from "../hooks/useDevices";
import type { CreateDeviceResponse } from "../lib/types";
import {
  type ConnectorOS,
  type PrinterChoice,
  assetFor,
  buildConfigYaml,
  detectOS,
  downloadUrlFor,
  runCommandFor,
} from "../lib/connectorSetup";

type Step = "os" | "name" | "download" | "run" | "waiting" | "success" | "printer";
const WAIT_TIMEOUT_MS = 75_000;

function download(filename: string, text: string) {
  const blob = new Blob([text], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

export function ConnectPrinterWizard({
  open,
  onClose,
}: {
  open: boolean;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const create = useCreateDevice();

  const [step, setStep] = useState<Step>("os");
  const [os, setOs] = useState<ConnectorOS | null>(null);
  const [macChip, setMacChip] = useState(false); // showing the Apple/Intel sub-choice
  const [name, setName] = useState("");
  const [created, setCreated] = useState<CreateDeviceResponse | null>(null);
  const [waitedOut, setWaitedOut] = useState(false);
  const [printerMode, setPrinterMode] = useState<"test" | "ip">("test");
  const [printerIp, setPrinterIp] = useState("");

  const deviceId = created?.device.id ?? null;
  const online = useDeviceOnline(deviceId, step === "waiting");

  // Reset everything when the modal is closed.
  useEffect(() => {
    if (!open) {
      setStep("os");
      setOs(null);
      setMacChip(false);
      setName("");
      setCreated(null);
      setWaitedOut(false);
      setPrinterMode("test");
      setPrinterIp("");
    }
  }, [open]);

  // Flip to success the moment the device reports online.
  useEffect(() => {
    if (step === "waiting" && online.data === true) setStep("success");
  }, [step, online.data]);

  // Give up waiting after the timeout → error hints (still on the waiting step).
  useEffect(() => {
    if (step !== "waiting") return;
    setWaitedOut(false);
    const h = setTimeout(() => setWaitedOut(true), WAIT_TIMEOUT_MS);
    return () => clearTimeout(h);
  }, [step, created]);

  const serverUrl = window.location.origin;
  const asset = os ? assetFor(os) : "";
  const configText = useMemo(() => {
    if (!os || !created) return "";
    const printer: PrinterChoice =
      printerMode === "ip" && printerIp.trim()
        ? { mode: "ip", ip: printerIp.trim() }
        : { mode: "test" };
    return buildConfigYaml({ serverUrl, token: created.token, os, printer });
  }, [os, created, serverUrl, printerMode, printerIp]);

  async function createAndAdvance() {
    const res = await create.mutateAsync(name.trim() || "Mój komputer");
    setCreated(res);
    setStep("download");
  }

  function chooseOs(next: ConnectorOS) {
    setOs(next);
    setMacChip(false);
    setStep("name");
  }

  const detection = useMemo(() => detectOS(), []);

  return (
    <Modal open={open} onClose={onClose} title={t("wizard.title")}>
      {step === "os" && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.osQuestion")}</p>
          <p className="text-sm text-slate-400">{t("wizard.osHint")}</p>
          {!macChip ? (
            <div className="grid grid-cols-2 gap-2">
              <OsTile emoji="🍎" title="Mac" sub={detection.family === "mac" ? t("wizard.detected") : "Apple / Intel"}
                onClick={() => setMacChip(true)} />
              <OsTile emoji="🪟" title="Windows" sub="10 / 11" onClick={() => chooseOs("windows")} />
              <OsTile emoji="🐧" title="Linux" sub="amd64 / Raspberry Pi" onClick={() => chooseOs("linux-amd64")} />
              <OsTile emoji="🔧" title={t("wizard.linuxArm")} sub="arm64 / arm" onClick={() => chooseOs("linux-arm64")} />
            </div>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-slate-300">{t("wizard.macChip")}</p>
              <div className="grid grid-cols-2 gap-2">
                <OsTile emoji="🍏" title="Apple (M1–M4)" sub={t("wizard.macApple")} onClick={() => chooseOs("mac-apple")} />
                <OsTile emoji="🖥" title="Intel" sub={t("wizard.macIntel")} onClick={() => chooseOs("mac-intel")} />
              </div>
              <button className="text-sm text-indigo-400" onClick={() => setMacChip(false)}>
                ← {t("common.back")}
              </button>
            </div>
          )}
        </div>
      )}

      {step === "name" && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.nameQuestion")}</p>
          <p className="text-sm text-slate-400">{t("wizard.nameHint")}</p>
          <Input value={name} onChange={(e) => setName(e.target.value)} placeholder={t("wizard.namePlaceholder")} />
          {create.isError && <p className="text-sm text-rose-400">{t("wizard.nameError")}</p>}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("os")}>← {t("common.back")}</Button>
            <Button onClick={() => void createAndAdvance()} disabled={create.isPending}>
              {t("wizard.createAndDownload")} →
            </Button>
          </div>
        </div>
      )}

      {step === "download" && os && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.downloadTitle")}</p>
          <p className="text-sm text-slate-400">{t("wizard.downloadHint")}</p>
          <a href={downloadUrlFor(os)} className="block rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 hover:border-indigo-500">
            📦 <span className="font-medium">{t("wizard.dlProgram")}</span>
            <span className="block text-xs text-slate-500">{asset}</span>
          </a>
          <button onClick={() => download("config.yaml", configText)}
            className="block w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-left hover:border-indigo-500">
            ⚙️ <span className="font-medium">{t("wizard.dlConfig")}</span>
            <span className="block text-xs text-slate-500">config.yaml — {t("wizard.dlConfigSub")}</span>
          </button>
          <p className="rounded-md border border-indigo-900 bg-indigo-950/40 px-3 py-2 text-xs text-indigo-300">
            🔒 {t("wizard.tokenPrivacy")}
          </p>
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("name")}>← {t("common.back")}</Button>
            <Button onClick={() => setStep("run")}>{t("common.next")} →</Button>
          </div>
        </div>
      )}

      {step === "run" && os && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.runTitle")}</p>
          <p className="text-sm text-slate-400">{t("wizard.runHint")}</p>
          <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 p-3">
            <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-slate-200">
              {runCommandFor(os, asset)}
            </code>
            <Button onClick={() => void navigator.clipboard?.writeText(runCommandFor(os, asset))}>
              {t("common.copy")}
            </Button>
          </div>
          <p className="rounded-md border border-amber-900 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
            💡 {t("wizard.keepOpen")}
          </p>
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("download")}>← {t("common.back")}</Button>
            <Button onClick={() => setStep("waiting")}>{t("wizard.checkConnection")} →</Button>
          </div>
        </div>
      )}

      {step === "waiting" && (
        <div className="space-y-4 py-4 text-center">
          {!waitedOut ? (
            <>
              <div className="mx-auto h-12 w-12 animate-spin rounded-full border-4 border-slate-600 border-t-indigo-400" />
              <p className="text-lg font-semibold">{t("wizard.waiting")}</p>
              <p className="text-sm text-slate-400">{t("wizard.waitingHint")}</p>
            </>
          ) : (
            <div className="space-y-3 text-left">
              <p className="text-lg font-semibold text-rose-400">{t("wizard.notSeen")}</p>
              <ul className="space-y-1 text-sm text-slate-300">
                <li>1. {t("wizard.tip1")}</li>
                <li>2. {t("wizard.tip2")}</li>
                <li>3. {t("wizard.tip3")}</li>
              </ul>
              <div className="flex justify-between pt-2">
                <Button variant="secondary" onClick={() => { setCreated(null); setStep("name"); }}>
                  {t("wizard.startOver")}
                </Button>
                <Button onClick={() => setWaitedOut(false)}>{t("wizard.keepChecking")} ↻</Button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "success" && (
        <div className="space-y-3 py-4 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full border-2 border-emerald-500/50 bg-emerald-950/40 text-2xl text-emerald-400">✓</div>
          <p className="text-lg font-semibold">{t("wizard.connected")} 🎉</p>
          <p className="text-sm text-slate-400">{t("wizard.connectedHint", { name: created?.device.name ?? "" })}</p>
          <div className="flex justify-center gap-2 pt-2">
            <Button variant="secondary" onClick={() => setStep("printer")}>{t("wizard.addPrinter")}</Button>
            <Button onClick={onClose}>{t("wizard.done")} ✓</Button>
          </div>
        </div>
      )}

      {step === "printer" && os && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.printerTitle")}</p>
          <p className="text-sm text-slate-400">{t("wizard.printerHint")}</p>
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={printerMode === "ip"} onChange={() => setPrinterMode("ip")} />
            {t("wizard.printerHasIp")}
          </label>
          {printerMode === "ip" && (
            <Input value={printerIp} onChange={(e) => setPrinterIp(e.target.value)} placeholder="192.168.1.50" />
          )}
          <label className="flex items-center gap-2 text-sm">
            <input type="radio" checked={printerMode === "test"} onChange={() => setPrinterMode("test")} />
            {t("wizard.printerTest")}
          </label>
          <p className="text-sm text-slate-400">{t("wizard.printerRedownload")}</p>
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={onClose}>{t("wizard.skip")}</Button>
            <Button onClick={() => download("config.yaml", configText)}>{t("wizard.downloadNewConfig")}</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function OsTile({ emoji, title, sub, onClick }: { emoji: string; title: string; sub: string; onClick: () => void }) {
  return (
    <button onClick={onClick}
      className="flex items-center gap-3 rounded-xl border border-slate-600 bg-slate-900 p-3 text-left hover:border-indigo-500">
      <span className="text-2xl">{emoji}</span>
      <span>
        <span className="block text-sm font-semibold">{title}</span>
        <span className="block text-xs text-slate-500">{sub}</span>
      </span>
    </button>
  );
}
```

- [ ] **Step 3: Typecheck + lint**

Run:
```bash
cd /var/www/html/BarcodeLabelGen/frontend
npm run typecheck && npm run lint
```
Expected: both clean. If `Modal` requires a `footer` and the inline buttons conflict, keep the buttons inside `children` (as written) — `footer` is optional per `components/ui/Modal.tsx`.

- [ ] **Step 4: Commit**

```bash
cd /var/www/html/BarcodeLabelGen
git add frontend/src/pages/ConnectPrinterWizard.tsx frontend/src/hooks/useDevices.ts
git commit -m "feat(wizard): ConnectPrinterWizard modal + useDeviceOnline poll (F38)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 3: Wire the wizard into Devices page + i18n

**Files:**
- Modify: `frontend/src/pages/DevicesPage.tsx` (primary "Connect a printer" button opens the wizard; keep the raw create modal as an advanced link)
- Modify: `frontend/src/i18n/locales/en.json`, `frontend/src/i18n/locales/pl.json` (all `wizard.*` keys + tweak `print.noDevices` copy)

**Interfaces:**
- Consumes: `ConnectPrinterWizard` (Task 2).
- Produces: user-facing wiring; no exported symbols.

- [ ] **Step 1: Mount the wizard on `DevicesPage.tsx`**

Add the import (near the other imports):
```tsx
import { ConnectPrinterWizard } from "./ConnectPrinterWizard";
```

Add state next to `const [showCreate, setShowCreate] = useState(false);`:
```tsx
  const [showWizard, setShowWizard] = useState(false);
```

Replace the header button block:
```tsx
        <Button onClick={() => setShowCreate(true)}>+ {t("devices.create")}</Button>
```
with:
```tsx
        <div className="flex items-center gap-3">
          <button className="text-sm text-slate-400 hover:text-slate-200" onClick={() => setShowCreate(true)}>
            {t("devices.createAdvanced")}
          </button>
          <Button onClick={() => setShowWizard(true)}>🖨 {t("wizard.connectButton")}</Button>
        </div>
```

Mount the wizard (next to where `CreateDeviceModal` is rendered — search for `<CreateDeviceModal`):
```tsx
      <ConnectPrinterWizard open={showWizard} onClose={() => setShowWizard(false)} />
```

- [ ] **Step 2: Add i18n keys to `frontend/src/i18n/locales/en.json`**

Add a `wizard` block (place it alphabetically or next to `devices`), and add `devices.createAdvanced`:

```json
  "wizard": {
    "connectButton": "Connect a printer",
    "title": "Connect a printer",
    "osQuestion": "Which computer is the printer connected to?",
    "osHint": "We detected your system — if it's right, just pick it.",
    "detected": "detected",
    "linuxArm": "Linux (ARM)",
    "macChip": "Which Mac chip? (Apple menu → About This Mac)",
    "macApple": "2020 and newer",
    "macIntel": "older Macs",
    "nameQuestion": "Name this computer",
    "nameHint": "Just a label so you recognise it later — e.g. \"Office Mac\".",
    "namePlaceholder": "Office Mac",
    "nameError": "That name is taken — try another.",
    "createAndDownload": "Create and get the files",
    "downloadTitle": "Download two files",
    "downloadHint": "Click both. They save to your Downloads folder. Nothing to edit — the settings are already filled in.",
    "dlProgram": "The connector program",
    "dlConfig": "Settings file",
    "dlConfigSub": "address and key already filled in",
    "tokenPrivacy": "The settings file holds your private key — keep it on your computer only.",
    "runTitle": "Run the program",
    "runHint": "Open Terminal, paste the line below and press Enter. That's it.",
    "keepOpen": "Leave that window open — the program must keep running for printing to work.",
    "checkConnection": "Check connection",
    "waiting": "Waiting for your computer to check in…",
    "waitingHint": "Usually a few seconds after you run the command. This updates by itself.",
    "notSeen": "I can't see your computer yet",
    "tip1": "Is Terminal open and the program still running? (don't close the window)",
    "tip2": "Is Tailscale on and connected (menu-bar icon)?",
    "tip3": "Did the pasted command run without a red error?",
    "startOver": "Start over",
    "keepChecking": "Keep checking",
    "connected": "Connected!",
    "connectedHint": "\"{{name}}\" is online now. You can print labels from the editor.",
    "addPrinter": "Add a printer (IP)",
    "done": "Done",
    "printerTitle": "Where is your printer?",
    "printerHint": "Enter the printer's IP address (on its screen or config printout). No printer yet? Use test mode — prints save to a file.",
    "printerHasIp": "My printer has an IP address",
    "printerTest": "Test mode for now (save to file)",
    "printerRedownload": "We'll make an updated settings file — download it, replace the old one, and run the program again.",
    "skip": "Skip",
    "downloadNewConfig": "Download updated settings"
  }
```

Also add inside the existing `devices` block: `"createAdvanced": "Advanced: create a token"`. And change `print.noDevices` value to end with a nudge, e.g. append: ` Connect one on the Devices page.` (keep any existing link markup intact — only adjust the sentence text).

- [ ] **Step 3: Add the SAME keys to `frontend/src/i18n/locales/pl.json`** (Polish, matching structure)

```json
  "wizard": {
    "connectButton": "Podłącz drukarkę",
    "title": "Podłącz drukarkę",
    "osQuestion": "Na jakim komputerze podłączasz drukarkę?",
    "osHint": "Wykryliśmy Twój system — jeśli się zgadza, po prostu go wybierz.",
    "detected": "wykryto",
    "linuxArm": "Linux (ARM)",
    "macChip": "Jaki procesor ma Mac? (menu Apple → O tym Macu)",
    "macApple": "2020 i nowsze",
    "macIntel": "starsze Maki",
    "nameQuestion": "Nazwij ten komputer",
    "nameHint": "To tylko etykieta, żebyś go rozpoznał — np. \"Mac w biurze\".",
    "namePlaceholder": "Mac w biurze",
    "nameError": "Ta nazwa jest zajęta — wybierz inną.",
    "createAndDownload": "Utwórz i pobierz pliki",
    "downloadTitle": "Pobierz dwa pliki",
    "downloadHint": "Kliknij oba. Zapiszą się w folderze Pobrane. Nic nie trzeba zmieniać — ustawienia są już wypełnione.",
    "dlProgram": "Program łączący",
    "dlConfig": "Plik ustawień",
    "dlConfigSub": "adres i klucz już wpisane",
    "tokenPrivacy": "Plik ustawień zawiera Twój prywatny klucz — trzymaj go tylko na swoim komputerze.",
    "runTitle": "Uruchom program",
    "runHint": "Otwórz Terminal, wklej poniższą linię i naciśnij Enter. To wszystko.",
    "keepOpen": "Zostaw to okno otwarte — program musi działać, żeby druk działał.",
    "checkConnection": "Sprawdź połączenie",
    "waiting": "Czekam, aż Twój komputer się zgłosi…",
    "waitingHint": "Zwykle kilka sekund po uruchomieniu komendy. To okno odświeży się samo.",
    "notSeen": "Nie widzę jeszcze Twojego komputera",
    "tip1": "Czy Terminal jest otwarty i program w nim działa? (nie zamykaj okna)",
    "tip2": "Czy Tailscale jest włączony i połączony (ikona w pasku menu)?",
    "tip3": "Czy wklejona komenda uruchomiła się bez czerwonego błędu?",
    "startOver": "Zacznij od nowa",
    "keepChecking": "Sprawdzaj dalej",
    "connected": "Połączono!",
    "connectedHint": "\"{{name}}\" jest teraz online. Możesz drukować etykiety z edytora.",
    "addPrinter": "Dodaj drukarkę (IP)",
    "done": "Gotowe",
    "printerTitle": "Gdzie jest Twoja drukarka?",
    "printerHint": "Podaj adres IP drukarki (na jej wyświetlaczu lub wydruku konfiguracji). Nie masz drukarki? Wybierz tryb testowy — wydruki zapiszą się do pliku.",
    "printerHasIp": "Moja drukarka ma adres IP",
    "printerTest": "Na razie testowo (zapis do pliku)",
    "printerRedownload": "Przygotujemy nowy plik ustawień — pobierz go, podmień stary i uruchom program ponownie.",
    "skip": "Pomiń",
    "downloadNewConfig": "Pobierz nowe ustawienia"
  }
```

Also add inside the Polish `devices` block: `"createAdvanced": "Zaawansowane: utwórz token"`, and adjust `print.noDevices` copy to nudge toward the Devices page (append e.g. ` Podłącz go na stronie Urządzenia.`).

If `common.back` / `common.next` / `common.copy` don't already exist in either file, reuse existing equivalents (search first); only add what's missing.

- [ ] **Step 4: Typecheck + lint + commit**

```bash
cd /var/www/html/BarcodeLabelGen/frontend
npm run typecheck && npm run lint
cd /var/www/html/BarcodeLabelGen
git add frontend/src/pages/DevicesPage.tsx frontend/src/i18n/locales/en.json frontend/src/i18n/locales/pl.json
git commit -m "feat(wizard): mount Connect-a-printer wizard on Devices page + i18n (F38)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
```

---

### Task 4: Release binaries, version bump, docs, v0.21.0

**Files:**
- Modify: `frontend/package.json`, `backend/pyproject.toml`, `backend/app/version.py`, `CHANGELOG.md`, `docs/PROJECT.md`

**Interfaces:**
- Consumes: the shipped wizard (Tasks 1–3).
- Produces: tag `v0.21.0`; a release carrying ALL SIX connector binaries (so `releases/latest/download/<asset>` links resolve).

- [ ] **Step 1: Add F38 to PROJECT.md**

In `docs/PROJECT.md`, after the `| F37 |` row, add:
```markdown
| F38 | Kreator „Podłącz drukarkę": prowadzony, nietechniczny setup konektora z poziomu aplikacji (auto-wykrycie systemu, gotowy `config.yaml` do pobrania, jedna komenda, wykrywanie „połączono" na żywo) — **zrealizowane w v0.21.0**; spec: `docs/superpowers/specs/2026-07-05-f38-connect-printer-wizard-design.md` | P1 |
```

- [ ] **Step 2: Bump all three version sources**

```bash
cd /var/www/html/BarcodeLabelGen
sed -i 's/"version": "0.20.1"/"version": "0.21.0"/' frontend/package.json
sed -i '0,/^version = "0.20.1"/s//version = "0.21.0"/' backend/pyproject.toml
sed -i 's/APP_VERSION = "0.20.1"/APP_VERSION = "0.21.0"/' backend/app/version.py
cd backend && .venv/bin/python -m pytest tests/test_version_sync.py -q
```
Expected: version-sync test passes (all three at 0.21.0).

- [ ] **Step 3: CHANGELOG `[0.21.0]`**

In `CHANGELOG.md`, insert above `## [0.20.1] — 2026-07-05`:
```markdown
## [0.21.0] — 2026-07-05

### Added
- **"Connect a printer" wizard (F38).** A guided, non-technical setup flow on
  the Devices page: it detects the user's OS, creates the device + token,
  generates a ready-to-run `config.yaml` (no manual editing, no quotes, no
  terminal heredocs), gives one copy-paste run command (with the macOS
  quarantine/chmod folded in), and detects the connection live ("waiting… →
  connected ✅"). Test-printer mode by default; real printer IP is an optional
  post-success step. Frontend-only — reuses the existing devices API; the
  token never appears in a URL. Built from the real friction of setting the
  connector up by hand.
```

And update the reference links — replace:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.20.1...HEAD
[0.20.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.20.1
```
with:
```markdown
[Unreleased]: https://github.com/AmigoUK/BarcodeLabelGen/compare/v0.21.0...HEAD
[0.21.0]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.21.0
[0.20.1]: https://github.com/AmigoUK/BarcodeLabelGen/releases/tag/v0.20.1
```

- [ ] **Step 4: Build all six connector binaries**

```bash
cd /var/www/html/BarcodeLabelGen/connector
./build-all.sh 2>&1 | tail -3
```
Expected: 6 binaries in `connector/dist/`.

- [ ] **Step 5: Commit, tag, push**

```bash
cd /var/www/html/BarcodeLabelGen
git add frontend/package.json backend/pyproject.toml backend/app/version.py CHANGELOG.md docs/PROJECT.md
git commit -m "chore(release): v0.21.0 — Connect-a-printer wizard (F38)

Co-Authored-By: Claude Fable 5 <noreply@anthropic.com>"
git tag -a v0.21.0 -m "v0.21.0 — Connect-a-printer wizard (F38)"
git push origin main && git push origin v0.21.0
```

- [ ] **Step 6: GitHub release WITH ALL SIX binaries**

```bash
cd /var/www/html/BarcodeLabelGen
gh release create v0.21.0 \
  --title "v0.21.0 — Connect-a-printer wizard (F38)" \
  --notes "$(awk '/^## \[0.21.0\]/{f=1;next} /^## \[0.20.1\]/{f=0} f' CHANGELOG.md)" \
  connector/dist/blg-connector-windows-amd64.exe \
  connector/dist/blg-connector-macos-intel \
  connector/dist/blg-connector-macos-apple \
  connector/dist/blg-connector-linux-amd64 \
  connector/dist/blg-connector-linux-arm64 \
  connector/dist/blg-connector-linux-arm
gh release view v0.21.0 --json assets --jq '.assets[].name'
```
Expected: release URL; all six asset names listed (so `releases/latest/download/<asset>` now resolves for every OS).

---

## Notes for the implementer

- **Frontend has no unit-test runner (by project convention).** Tasks 1–3 gate on `npm run typecheck` + `npm run lint`. Behaviour is verified end-to-end by the controller after Task 4: rebuild the stack, drive the wizard in headless Chromium on the live instance, download the generated `config.yaml`, run the real connector on the server with it, and confirm the wizard flips to "Połączono".
- **Do not touch `connector/` or `backend/` code** — F38 is frontend + release only. The one backend file that changes is `app/version.py` (the version constant, Task 4), which the version-sync test covers.
- Before editing i18n, grep both locale files for `common.back`, `common.next`, `common.copy`, `common.loading` — reuse what exists; only add missing keys.
- The wizard renders its own step buttons inside the `Modal` body (not the `footer` slot) — this is intentional so each step controls its own navigation.
