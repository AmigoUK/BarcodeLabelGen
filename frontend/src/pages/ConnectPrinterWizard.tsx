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
