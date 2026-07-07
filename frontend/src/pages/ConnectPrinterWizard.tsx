/**
 * F38/F40 — "Connect a printer" wizard. Guides a non-technical user from zero
 * to a connected connector: detect OS → name the computer (creates
 * device+token) → download ONE self-contained installer (F40) → run it →
 * live "connected" detection → discovered printers (polled) → optional
 * virtual-printer guide. No manual file editing anywhere.
 */

import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { useCreateDevice, useDeviceOnline, useDevices } from "../hooks/useDevices";
import type { CreateDeviceResponse } from "../lib/types";
import { detectOS } from "../lib/connectorSetup";
import { type InstallerFamily, installerFor } from "../lib/installerSetup";

type Step = "os" | "name" | "install" | "waiting" | "success" | "printers" | "virtual";
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

export function ConnectPrinterWizard({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const create = useCreateDevice();
  const devices = useDevices();

  const [step, setStep] = useState<Step>("os");
  const [family, setFamily] = useState<InstallerFamily | null>(null);
  const [name, setName] = useState("");
  const [created, setCreated] = useState<CreateDeviceResponse | null>(null);
  const [waitedOut, setWaitedOut] = useState(false);
  const [recheckNonce, setRecheckNonce] = useState(0);
  const [printerIp, setPrinterIp] = useState("");

  const deviceId = created?.device.id ?? null;
  const online = useDeviceOnline(deviceId, step === "waiting");

  // Reset everything when the modal is closed.
  useEffect(() => {
    if (!open) {
      setStep("os");
      setFamily(null);
      setName("");
      setCreated(null);
      setWaitedOut(false);
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
  }, [step, created, recheckNonce]);

  // Poll the devices list while the printers step is open, so newly-detected
  // local printers show up without the user having to reopen the wizard.
  useEffect(() => {
    if (step !== "printers") return;
    const h = setInterval(() => void devices.refetch(), 5000);
    return () => clearInterval(h);
  }, [step, devices]);

  const serverUrl = window.location.origin;
  const livePrinters = devices.data?.find((d) => d.id === created?.device.id)?.printers ?? [];

  const installer = useMemo(() => {
    if (!family || !created) return null;
    return installerFor(family, { serverUrl, token: created.token, printer: { mode: "test" } });
  }, [family, created, serverUrl]);

  async function createAndAdvance() {
    const res = await create.mutateAsync(name.trim() || t("wizard.namePlaceholder"));
    setCreated(res);
    setStep("install");
  }

  function chooseFamily(next: InstallerFamily) {
    setFamily(next);
    setStep("name");
  }

  function downloadWithIpPrinter() {
    if (!family || !created || !printerIp.trim()) return;
    const { filename, content } = installerFor(family, {
      serverUrl,
      token: created.token,
      printer: { mode: "ip", ip: printerIp.trim() },
    });
    download(filename, content);
  }

  const detection = useMemo(() => detectOS(), []);

  return (
    <Modal open={open} onClose={onClose} title={t("wizard.title")}>
      {step === "os" && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.osQuestion")}</p>
          <p className="text-sm text-slate-400">{t("wizard.osHint")}</p>
          <div className="grid grid-cols-2 gap-2">
            <OsTile
              emoji="🍎"
              title="Mac"
              sub={detection.family === "mac" ? t("wizard.detected") : "macOS"}
              onClick={() => chooseFamily("mac")}
            />
            <OsTile
              emoji="🪟"
              title="Windows"
              sub={detection.family === "windows" ? t("wizard.detected") : "10 / 11"}
              onClick={() => chooseFamily("windows")}
            />
            <OsTile
              emoji="🐧"
              title="Linux"
              sub={detection.family === "linux" ? t("wizard.detected") : "amd64 / arm64"}
              onClick={() => chooseFamily("linux")}
            />
          </div>
        </div>
      )}

      {step === "name" && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.nameQuestion")}</p>
          <p className="text-sm text-slate-400">{t("wizard.nameHint")}</p>
          <Input
            value={name}
            onChange={(e) => setName(e.target.value)}
            placeholder={t("wizard.namePlaceholder")}
          />
          {create.isError && <p className="text-sm text-rose-400">{t("wizard.nameError")}</p>}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("os")}>
              ← {t("common.back")}
            </Button>
            <Button onClick={() => void createAndAdvance()} disabled={create.isPending}>
              {t("wizard.createAndDownload")} →
            </Button>
          </div>
        </div>
      )}

      {step === "install" && family && installer && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.installTitle")}</p>
          <p className="text-sm text-slate-400">{t("wizard.installHint")}</p>
          <button
            onClick={() => download(installer.filename, installer.content)}
            className="block w-full rounded-lg border border-slate-700 bg-slate-900 px-4 py-3 text-left hover:border-indigo-500"
          >
            📦 <span className="font-medium">{t("wizard.installDownload")}</span>
            <span className="block text-xs text-slate-500">{installer.filename}</span>
          </button>
          <p className="text-sm text-slate-300">{t(`wizard.installRun.${family}`)}</p>
          {family === "mac" && <p className="text-xs text-slate-500">{t("wizard.unsignedNote")}</p>}
          <p className="rounded-md border border-indigo-900 bg-indigo-950/40 px-3 py-2 text-xs text-indigo-300">
            🔒 {t("wizard.tokenPrivacy")}
          </p>
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("name")}>
              ← {t("common.back")}
            </Button>
            <Button onClick={() => setStep("waiting")}>{t("common.next")} →</Button>
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
                <Button
                  variant="secondary"
                  onClick={() => {
                    setCreated(null);
                    setStep("name");
                  }}
                >
                  {t("wizard.startOver")}
                </Button>
                <Button
                  onClick={() => {
                    setWaitedOut(false);
                    setRecheckNonce((n) => n + 1);
                  }}
                >
                  {t("wizard.keepChecking")} ↻
                </Button>
              </div>
            </div>
          )}
        </div>
      )}

      {step === "success" && (
        <div className="space-y-3 py-4 text-center">
          <div className="mx-auto grid h-14 w-14 place-items-center rounded-full border-2 border-emerald-500/50 bg-emerald-950/40 text-2xl text-emerald-400">
            ✓
          </div>
          <p className="text-lg font-semibold">{t("wizard.connected")} 🎉</p>
          <p className="text-sm text-slate-400">
            {t("wizard.connectedHint", { name: created?.device.name ?? "" })}
          </p>
          <div className="flex justify-center gap-2 pt-2">
            <Button variant="secondary" onClick={() => setStep("printers")}>
              {t("wizard.addPrinter")} →
            </Button>
            <Button onClick={onClose}>{t("wizard.finish")}</Button>
          </div>
        </div>
      )}

      {step === "printers" && family && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.printersTitle")}</p>
          <p className="text-sm text-slate-400">{t("wizard.printersHint")}</p>

          {livePrinters.length === 0 ? (
            <p className="rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-400">
              {t("wizard.printersEmpty")}
            </p>
          ) : (
            <ul className="space-y-1">
              {livePrinters.map((p) => (
                <li
                  key={p.name}
                  className="flex items-center justify-between rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm"
                >
                  <span>{p.name}</span>
                  {p.kind === "local" && (
                    <span className="rounded-full bg-indigo-950/60 px-2 py-0.5 text-xs text-indigo-300">
                      {t("wizard.printersLocalBadge")}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          )}

          <details className="rounded border border-indigo-900/60 bg-slate-900/40 p-2">
            <summary className="cursor-pointer text-xs font-medium text-indigo-300">
              {t("wizard.advancedIp")}
            </summary>
            <div className="mt-2 space-y-2">
              <Input
                value={printerIp}
                onChange={(e) => setPrinterIp(e.target.value)}
                placeholder="192.168.1.50"
              />
              <Button
                variant="secondary"
                onClick={downloadWithIpPrinter}
                disabled={!printerIp.trim()}
              >
                {t("wizard.downloadWithPrinter")}
              </Button>
              <p className="text-[10px] text-slate-500">{t("wizard.rerunHint")}</p>
            </div>
          </details>

          <button
            className="text-sm text-indigo-400 hover:text-indigo-300"
            onClick={() => setStep("virtual")}
          >
            {t("wizard.virtualLink")}
          </button>

          <div className="flex justify-end pt-2">
            <Button onClick={onClose}>{t("wizard.finish")}</Button>
          </div>
        </div>
      )}

      {step === "virtual" && family && (
        <div className="space-y-3">
          <p className="text-lg font-semibold">{t("wizard.virtualTitle")}</p>
          {family === "windows" ? (
            <ol className="space-y-1 text-sm text-slate-300">
              <li>1. {t("wizard.virtualWinStep1")}</li>
              <li>2. {t("wizard.virtualWinStep2")}</li>
              <li>3. {t("wizard.virtualWinStep3")}</li>
              <li>4. {t("wizard.virtualWinStep4")}</li>
            </ol>
          ) : (
            <div className="space-y-2">
              <p className="text-sm text-slate-400">{t("wizard.virtualCmd")}</p>
              <div className="flex items-center gap-2 rounded-lg border border-slate-700 bg-slate-900 p-3">
                <code className="flex-1 overflow-x-auto whitespace-nowrap font-mono text-xs text-slate-200">
                  {t(family === "mac" ? "wizard.virtualCmdMac" : "wizard.virtualCmdLinux")}
                </code>
                <Button
                  onClick={() =>
                    void navigator.clipboard?.writeText(
                      t(family === "mac" ? "wizard.virtualCmdMac" : "wizard.virtualCmdLinux"),
                    )
                  }
                >
                  {t("common.copy")}
                </Button>
              </div>
              <p className="text-sm text-slate-400">{t("wizard.virtualHintUnix")}</p>
            </div>
          )}
          <div className="flex justify-between pt-2">
            <Button variant="secondary" onClick={() => setStep("printers")}>
              ← {t("common.back")}
            </Button>
            <Button onClick={onClose}>{t("wizard.finish")}</Button>
          </div>
        </div>
      )}
    </Modal>
  );
}

function OsTile({
  emoji,
  title,
  sub,
  onClick,
}: {
  emoji: string;
  title: string;
  sub: string;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className="flex items-center gap-3 rounded-xl border border-slate-600 bg-slate-900 p-3 text-left hover:border-indigo-500"
    >
      <span className="text-2xl">{emoji}</span>
      <span>
        <span className="block text-sm font-semibold">{title}</span>
        <span className="block text-xs text-slate-500">{sub}</span>
      </span>
    </button>
  );
}
