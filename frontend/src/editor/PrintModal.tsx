/**
 * Print via the local connector: generate ZPL from the live canvas, queue
 * it for a device, then watch the job until the agent reports done/error.
 */

import { useQuery } from "@tanstack/react-query";
import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { useDevices } from "../hooks/useDevices";
import { ApiError } from "../lib/api";
import { useCreatePrintJob, usePrintJobs } from "../hooks/usePrintJobs";
import { useGenerateZpl } from "../hooks/useZpl";
import { fetchLocalPrinters, printLocal, probeLocalAgent } from "../lib/localAgent";
import type { Device } from "../lib/types";
import type { CanvasData } from "./types";

/** Select value for the loopback fast path — not a real device id. */
const LOCAL = "local" as const;

const ONLINE_WINDOW_MS = 60_000;

function isOnline(device: Device): boolean {
  if (!device.last_seen_at) return false;
  return Date.now() - new Date(device.last_seen_at).getTime() < ONLINE_WINDOW_MS;
}

type Props = {
  open: boolean;
  onClose: () => void;
  canvas: CanvasData;
};

export function PrintModal({ open, onClose, canvas }: Props) {
  const { t } = useTranslation();
  const { data: devices } = useDevices();
  const generateZpl = useGenerateZpl();
  const createJob = useCreatePrintJob();

  const [deviceId, setDeviceId] = useState<number | "" | typeof LOCAL>("");
  const [printer, setPrinter] = useState("");
  const [copies, setCopies] = useState(1);
  const [dpi, setDpi] = useState(203);
  const [watchedJobId, setWatchedJobId] = useState<number | null>(null);
  const [localOutcome, setLocalOutcome] = useState<"done" | string | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // F21 fast path: is a connector running on THIS machine? Probe once per
  // dialog open; any failure (no agent, browser policy) means queue-only.
  const localAgent = useQuery({
    queryKey: ["local-agent"],
    queryFn: probeLocalAgent,
    enabled: open,
    staleTime: 10_000,
    retry: false,
  });
  const localAvailable = !!localAgent.data;
  const localPrinters = useQuery({
    queryKey: ["local-agent", "printers"],
    queryFn: fetchLocalPrinters,
    enabled: open && localAvailable,
    retry: false,
  });

  const selectedDevice = useMemo(
    () => (typeof deviceId === "number" ? (devices?.find((d) => d.id === deviceId) ?? null) : null),
    [devices, deviceId],
  );

  // Preselect: the local agent when present, else the first online device.
  useEffect(() => {
    if (!open || deviceId !== "") return;
    if (localAvailable) {
      setDeviceId(LOCAL);
      return;
    }
    if (localAgent.isPending) return; // wait for the probe before defaulting
    if (!devices || devices.length === 0) return;
    const preferred = devices.find(isOnline) ?? devices[0];
    setDeviceId(preferred.id);
  }, [open, devices, deviceId, localAvailable, localAgent.isPending]);

  // Keep the printer choice in sync with the selected target's printer list.
  useEffect(() => {
    const names =
      deviceId === LOCAL
        ? (localPrinters.data?.map((p) => p.name) ?? [])
        : (selectedDevice?.printers.map((p) => p.name) ?? []);
    if (names.length > 0 && !names.includes(printer)) setPrinter(names[0]);
  }, [deviceId, selectedDevice, localPrinters.data, printer]);

  const { data: jobs } = usePrintJobs({ watch: watchedJobId !== null });
  const watchedJob = watchedJobId !== null ? jobs?.find((j) => j.id === watchedJobId) : undefined;
  const jobSettled = watchedJob?.status === "done" || watchedJob?.status === "error";

  const close = () => {
    setWatchedJobId(null);
    setLocalOutcome(null);
    setSubmitError(null);
    generateZpl.reset();
    createJob.reset();
    onClose();
  };

  const submit = async () => {
    if (deviceId === "" || !printer.trim()) return;
    setSubmitError(null);
    try {
      const { zpl } = await generateZpl.mutateAsync({ canvas_data: canvas, dpi });
      if (deviceId === LOCAL) {
        // Fast path: straight to the loopback agent, no server round-trip.
        try {
          await printLocal(printer.trim(), zpl, copies);
          setLocalOutcome("done");
        } catch (err) {
          setLocalOutcome(err instanceof Error ? err.message : String(err));
        }
        return;
      }
      const job = await createJob.mutateAsync({
        device_id: deviceId,
        printer: printer.trim(),
        zpl,
        copies,
      });
      setWatchedJobId(job.id);
    } catch (err) {
      if (err instanceof ApiError && err.code === "invalid_zpl") {
        setSubmitError(t("zpl.invalidZpl"));
      } else {
        setSubmitError(err instanceof Error ? err.message : t("auth.errors.generic"));
      }
    }
  };

  if (!open) return null;

  // --- local fast-path result ---------------------------------------------
  if (localOutcome !== null) {
    return (
      <Modal
        open
        onClose={close}
        title={t("print.title")}
        footer={<Button onClick={close}>{t("common.close")}</Button>}
      >
        {localOutcome === "done" ? (
          <p className="text-sm text-emerald-400">✓ {t("print.done")}</p>
        ) : (
          <div className="space-y-1 text-sm text-rose-300">
            <p>✗ {t("print.failed")}</p>
            <code className="block rounded bg-slate-950 p-2 text-xs">{localOutcome}</code>
          </div>
        )}
      </Modal>
    );
  }

  // --- watching a submitted job ------------------------------------------
  if (watchedJobId !== null) {
    return (
      <Modal
        open
        onClose={close}
        title={t("print.title")}
        footer={<Button onClick={close}>{t("common.close")}</Button>}
      >
        {!jobSettled && (
          <p className="text-sm text-slate-300">
            <span className="mr-2 inline-block animate-pulse">🖨</span>
            {watchedJob?.status === "sent" ? t("print.sentToAgent") : t("print.queued")}
          </p>
        )}
        {watchedJob?.status === "done" && (
          <p className="text-sm text-emerald-400">✓ {t("print.done")}</p>
        )}
        {watchedJob?.status === "error" && (
          <div className="space-y-1 text-sm text-rose-300">
            <p>✗ {t("print.failed")}</p>
            {watchedJob.error && (
              <code className="block rounded bg-slate-950 p-2 text-xs">{watchedJob.error}</code>
            )}
          </div>
        )}
      </Modal>
    );
  }

  // --- form ----------------------------------------------------------------
  const noDevices = devices !== undefined && devices.length === 0 && !localAvailable;
  const reportedPrinters =
    deviceId === LOCAL
      ? (localPrinters.data?.map((p) => ({ name: p.name, host: p.host })) ?? [])
      : (selectedDevice?.printers ?? []);
  const submitting = generateZpl.isPending || createJob.isPending;

  return (
    <Modal
      open
      onClose={close}
      title={t("print.title")}
      footer={
        <>
          <Button variant="secondary" onClick={close}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() => void submit()}
            disabled={submitting || deviceId === "" || !printer.trim()}
          >
            {submitting ? t("print.submitting") : t("print.submit")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        {noDevices ? (
          <p className="text-sm text-slate-300">
            {t("print.noDevices")}{" "}
            <Link to="/devices" className="text-indigo-400 hover:text-indigo-300">
              {t("nav.devices")} →
            </Link>
          </p>
        ) : (
          <>
            <Select
              label={t("print.device")}
              value={deviceId}
              onChange={(e) => {
                setDeviceId(e.target.value === LOCAL ? LOCAL : Number(e.target.value));
                setPrinter("");
              }}
            >
              {localAvailable && (
                <option value={LOCAL}>
                  ⚡ {t("print.localDevice", { version: localAgent.data?.version })}
                </option>
              )}
              {devices?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {isOnline(d) ? `● ${t("devices.online")}` : `○ ${t("devices.offline")}`}
                </option>
              ))}
            </Select>
            {deviceId === LOCAL && (
              <p className="text-xs text-emerald-400">{t("print.localHint")}</p>
            )}
            {selectedDevice && !isOnline(selectedDevice) && (
              <p className="text-xs text-amber-400">{t("print.deviceOfflineHint")}</p>
            )}
            {reportedPrinters.length > 0 ? (
              <Select
                label={t("print.printer")}
                value={printer}
                onChange={(e) => setPrinter(e.target.value)}
              >
                {reportedPrinters.map((p) => (
                  <option key={p.name} value={p.name}>
                    {p.name} ({p.host})
                  </option>
                ))}
              </Select>
            ) : (
              <Input
                label={t("print.printer")}
                value={printer}
                onChange={(e) => setPrinter(e.target.value)}
                placeholder={t("print.printerPlaceholder")}
                hint={t("print.printerManualHint")}
              />
            )}
            <div className="grid grid-cols-2 gap-3">
              <Input
                label={t("print.copies")}
                type="number"
                min={1}
                max={1000}
                value={copies}
                onChange={(e) => setCopies(Math.max(1, Number(e.target.value) || 1))}
              />
              <Select
                label={t("zpl.dpi")}
                value={dpi}
                onChange={(e) => setDpi(Number(e.target.value))}
              >
                <option value={203}>203 dpi (8 dpmm)</option>
                <option value={300}>300 dpi (12 dpmm)</option>
              </Select>
            </div>
          </>
        )}
        {submitError && (
          <div className="rounded-md border border-rose-900 bg-rose-950/50 px-3 py-2 text-sm text-rose-300">
            {submitError}
          </div>
        )}
      </div>
    </Modal>
  );
}
