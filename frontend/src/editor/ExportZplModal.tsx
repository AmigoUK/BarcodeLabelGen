import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { downloadJobPdf, useDatasets, useJobStatus } from "../hooks/useDatasets";
import { type ZplWarning, useGenerateZpl, useSubmitZplBatch } from "../hooks/useZpl";
import type { CanvasData } from "./types";

type Props = {
  open: boolean;
  onClose: () => void;
  canvas: CanvasData;
  templateId: number;
  templateName: string;
};

type Mode = "template" | "batch";

function safeName(name: string): string {
  return name.replace(/[^A-Za-z0-9._-]+/g, "_") || "labels";
}

export function ExportZplModal({ open, onClose, canvas, templateId, templateName }: Props) {
  const { t } = useTranslation();
  const [mode, setMode] = useState<Mode>("template");
  const [dpi, setDpi] = useState(203);

  const generate = useGenerateZpl();
  const [zpl, setZpl] = useState("");
  const [warnings, setWarnings] = useState<ZplWarning[]>([]);
  const [copied, setCopied] = useState(false);

  // Live preview: (re)generate on open and whenever the canvas or DPI
  // changes, debounced so dragging an element doesn't spam the backend.
  useEffect(() => {
    if (!open || mode !== "template") return;
    const handle = setTimeout(() => {
      generate.mutate(
        { canvas_data: canvas, dpi },
        {
          onSuccess: (r) => {
            setZpl(r.zpl);
            setWarnings(r.warnings);
          },
        },
      );
    }, 300);
    return () => clearTimeout(handle);
    // generate is stable across renders (react-query); intentionally omitted
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, mode, canvas, dpi]);

  const handleCopy = () => {
    void navigator.clipboard.writeText(zpl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const handleDownload = () => {
    const blob = new Blob([zpl], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName(templateName)}.zpl`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  };

  const genError = generate.error
    ? generate.error instanceof Error
      ? generate.error.message
      : String(generate.error)
    : null;

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("zpl.exportTitle")}
      footer={
        <Button variant="ghost" onClick={onClose}>
          {t("common.close")}
        </Button>
      }
    >
      <div className="space-y-3">
        <div className="flex items-center gap-3">
          <div className="w-44">
            <Select
              label={t("zpl.mode")}
              value={mode}
              onChange={(e) => setMode(e.target.value as Mode)}
            >
              <option value="template">{t("zpl.modeTemplate")}</option>
              <option value="batch">{t("zpl.modeBatch")}</option>
            </Select>
          </div>
          <div className="w-40">
            <Select
              label={t("zpl.dpi")}
              value={dpi}
              onChange={(e) => setDpi(Number(e.target.value))}
            >
              <option value={203}>203 dpi (8 dpmm)</option>
              <option value={300}>300 dpi (12 dpmm)</option>
            </Select>
          </div>
        </div>

        {mode === "template" ? (
          <TemplatePanel
            zpl={zpl}
            pending={generate.isPending}
            error={genError}
            warnings={warnings}
            copied={copied}
            onCopy={handleCopy}
            onDownload={handleDownload}
          />
        ) : (
          <BatchPanel templateId={templateId} templateName={templateName} dpi={dpi} />
        )}
      </div>
    </Modal>
  );
}

function TemplatePanel({
  zpl,
  pending,
  error,
  warnings,
  copied,
  onCopy,
  onDownload,
}: {
  zpl: string;
  pending: boolean;
  error: string | null;
  warnings: ZplWarning[];
  copied: boolean;
  onCopy: () => void;
  onDownload: () => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-2">
      <p className="text-sm text-slate-400">{t("zpl.exportHelp")}</p>
      <pre className="h-64 overflow-auto rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100">
        {pending && !zpl ? t("common.loading") : zpl}
      </pre>
      {error && <p className="text-sm text-rose-400">{error}</p>}
      {warnings.length > 0 && (
        <ul className="max-h-20 overflow-auto rounded bg-amber-900/30 p-2 text-xs text-amber-200">
          {warnings.map((w, i) => (
            <li key={i}>• {w.message}</li>
          ))}
        </ul>
      )}
      <div className="flex gap-2">
        <Button onClick={onCopy} disabled={!zpl}>
          {copied ? t("zpl.copied") : t("zpl.copy")}
        </Button>
        <Button variant="secondary" onClick={onDownload} disabled={!zpl}>
          {t("zpl.download")}
        </Button>
      </div>
    </div>
  );
}

function BatchPanel({
  templateId,
  templateName,
  dpi,
}: {
  templateId: number;
  templateName: string;
  dpi: number;
}) {
  const { t } = useTranslation();
  const datasets = useDatasets();
  const submit = useSubmitZplBatch();
  const [datasetId, setDatasetId] = useState<number | null>(null);
  const [jobId, setJobId] = useState<string | null>(null);
  const job = useJobStatus(jobId);

  useEffect(() => {
    if (job.data?.status === "done" && jobId) {
      void downloadJobPdf(jobId, `${safeName(templateName)}.zpl`);
      setJobId(null);
    }
  }, [job.data?.status, jobId, templateName]);

  const handleGenerate = () => {
    if (datasetId === null) return;
    submit.mutate(
      { template_id: templateId, dataset_id: datasetId, dpi },
      { onSuccess: (r) => setJobId(r.job_id) },
    );
  };

  const submitError = submit.error
    ? submit.error instanceof Error
      ? submit.error.message
      : String(submit.error)
    : null;
  const running =
    submit.isPending ||
    (job.data != null && job.data.status !== "done" && job.data.status !== "error");

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-400">{t("zpl.batchHelp")}</p>
      <Select
        label={t("zpl.dataset")}
        value={datasetId ?? ""}
        onChange={(e) => setDatasetId(e.target.value ? Number(e.target.value) : null)}
      >
        <option value="">{t("zpl.datasetPick")}</option>
        {(datasets.data ?? []).map((d) => (
          <option key={d.id} value={d.id}>
            {d.original_filename} ({d.row_count})
          </option>
        ))}
      </Select>
      <Button onClick={handleGenerate} disabled={datasetId === null || running}>
        {running ? t("zpl.generating") : t("zpl.generateBatch")}
      </Button>
      {job.data && job.data.status !== "done" && (
        <p className="text-xs text-slate-400">
          {job.data.status} — {job.data.progress}/{job.data.total}
        </p>
      )}
      {job.data?.status === "error" && <p className="text-sm text-rose-400">{job.data.error}</p>}
      {submitError && <p className="text-sm text-rose-400">{submitError}</p>}
    </div>
  );
}
