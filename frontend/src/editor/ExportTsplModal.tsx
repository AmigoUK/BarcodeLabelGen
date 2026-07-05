import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { type TsplWarning, useGenerateTspl } from "../hooks/useTspl";
import type { CanvasData } from "./types";

type Props = {
  open: boolean;
  onClose: () => void;
  canvas: CanvasData;
  templateName: string;
};

function safeName(name: string): string {
  return name.replace(/[^A-Za-z0-9._-]+/g, "_") || "labels";
}

export function ExportTsplModal({ open, onClose, canvas, templateName }: Props) {
  const { t } = useTranslation();
  const [dpi, setDpi] = useState(203);

  const generate = useGenerateTspl();
  const [tspl, setTspl] = useState("");
  const [warnings, setWarnings] = useState<TsplWarning[]>([]);
  const [copied, setCopied] = useState(false);

  // Live preview: (re)generate on open and whenever the canvas or DPI
  // changes, debounced so dragging an element doesn't spam the backend.
  useEffect(() => {
    if (!open) return;
    const handle = setTimeout(() => {
      generate.mutate(
        { canvas_data: canvas, dpi },
        {
          onSuccess: (r) => {
            setTspl(r.tspl);
            setWarnings(r.warnings);
          },
        },
      );
    }, 300);
    return () => clearTimeout(handle);
    // generate is stable across renders (react-query); intentionally omitted
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, canvas, dpi]);

  const handleCopy = () => {
    void navigator.clipboard.writeText(tspl).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  const handleDownload = () => {
    const blob = new Blob([tspl], { type: "text/plain;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${safeName(templateName)}.txt`;
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
      title={t("tspl.exportTitle")}
      footer={
        <Button variant="ghost" onClick={onClose}>
          {t("common.close")}
        </Button>
      }
    >
      <div className="space-y-3">
        <div className="w-40">
          <Select
            label={t("tspl.dpi")}
            value={dpi}
            onChange={(e) => setDpi(Number(e.target.value))}
          >
            <option value={203}>203 dpi (8 dpmm)</option>
            <option value={300}>300 dpi (12 dpmm)</option>
          </Select>
        </div>

        <p className="text-sm text-slate-400">{t("tspl.exportHelp")}</p>
        <pre className="h-64 overflow-auto rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100">
          {generate.isPending && !tspl ? t("common.loading") : tspl}
        </pre>
        {genError && <p className="text-sm text-rose-400">{genError}</p>}
        {warnings.length > 0 && (
          <ul className="max-h-20 overflow-auto rounded bg-amber-900/30 p-2 text-xs text-amber-200">
            {warnings.map((w, i) => (
              <li key={i}>• {w.message}</li>
            ))}
          </ul>
        )}
        <div className="flex gap-2">
          <Button onClick={handleCopy} disabled={!tspl}>
            {copied ? t("tspl.copied") : t("tspl.copy")}
          </Button>
          <Button variant="secondary" onClick={handleDownload} disabled={!tspl}>
            {t("tspl.download")}
          </Button>
        </div>
      </div>
    </Modal>
  );
}
