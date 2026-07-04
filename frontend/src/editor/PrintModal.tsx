/**
 * Print via the local connector: generate ZPL from the live canvas, queue
 * it for a device, then watch the job until the agent reports done/error.
 */

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
import type { Device } from "../lib/types";
import type { CanvasData } from "./types";

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

  const [deviceId, setDeviceId] = useState<number | "">("");
  const [printer, setPrinter] = useState("");
  const [copies, setCopies] = useState(1);
  const [dpi, setDpi] = useState(203);
  const [watchedJobId, setWatchedJobId] = useState<number | null>(null);
  const [submitError, setSubmitError] = useState<string | null>(null);

  const selectedDevice = useMemo(
    () => devices?.find((d) => d.id === deviceId) ?? null,
    [devices, deviceId],
  );

  // Preselect the first online device (or the first one at all).
  useEffect(() => {
    if (!open || deviceId !== "" || !devices || devices.length === 0) return;
    const preferred = devices.find(isOnline) ?? devices[0];
    setDeviceId(preferred.id);
  }, [open, devices, deviceId]);

  // Keep the printer choice in sync with what the device reported.
  useEffect(() => {
    if (!selectedDevice) return;
    const names = selectedDevice.printers.map((p) => p.name);
    if (names.length > 0 && !names.includes(printer)) setPrinter(names[0]);
  }, [selectedDevice, printer]);

  const { data: jobs } = usePrintJobs({ watch: watchedJobId !== null });
  const watchedJob = watchedJobId !== null ? jobs?.find((j) => j.id === watchedJobId) : undefined;
  const jobSettled = watchedJob?.status === "done" || watchedJob?.status === "error";

  const close = () => {
    setWatchedJobId(null);
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
  const noDevices = devices !== undefined && devices.length === 0;
  const reportedPrinters = selectedDevice?.printers ?? [];
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
                setDeviceId(Number(e.target.value));
                setPrinter("");
              }}
            >
              {devices?.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.name} {isOnline(d) ? `● ${t("devices.online")}` : `○ ${t("devices.offline")}`}
                </option>
              ))}
            </Select>
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
