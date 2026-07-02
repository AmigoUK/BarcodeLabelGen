import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { type ZplParseResult, useParseZpl } from "../hooks/useZpl";
import type { CanvasData } from "./types";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Current label size — used as the target for DPI auto-detection and to
   *  flag content that would fall outside the label. */
  currentStage: { width_mm: number; height_mm: number };
  /** Called with the parsed canvas when the user confirms the import.
   *  Replaces the editor objects — the caller keeps the label size. */
  onImported: (canvas: CanvasData) => void;
};

type DpiChoice = "auto" | "203" | "300";

/** Largest right/bottom edge (mm) reached by any object — a rough content
 *  bounding box to detect a wrong-DPI import (everything scaled too big). */
function contentBounds(canvas: CanvasData): { right: number; bottom: number } {
  let right = 0;
  let bottom = 0;
  for (const o of canvas.objects) {
    const rec = o as unknown as Record<string, unknown>;
    const x = typeof rec.x === "number" ? rec.x : 0;
    const y = typeof rec.y === "number" ? rec.y : 0;
    const w = typeof rec.width === "number" ? rec.width : 0;
    const h =
      typeof rec.height === "number"
        ? rec.height
        : o.type === "text" && typeof rec.fontSize === "number"
          ? rec.fontSize
          : 0;
    right = Math.max(right, x + w);
    bottom = Math.max(bottom, y + h);
  }
  return { right, bottom };
}

export function ImportZplModal({ open, onClose, currentStage, onImported }: Props) {
  const { t } = useTranslation();
  const parse = useParseZpl();
  const [zpl, setZpl] = useState("");
  const [dpi, setDpi] = useState<DpiChoice>("auto");
  const [result, setResult] = useState<ZplParseResult | null>(null);

  const reset = () => {
    setZpl("");
    setResult(null);
    parse.reset();
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  // Any change to the input invalidates a previous analysis.
  const onZplChange = (v: string) => {
    setZpl(v);
    setResult(null);
  };
  const onDpiChange = (v: DpiChoice) => {
    setDpi(v);
    setResult(null);
  };

  const handleAnalyze = () => {
    parse.mutate(
      {
        zpl,
        dpi: dpi === "auto" ? "auto" : Number(dpi),
        target_width_mm: currentStage.width_mm,
        target_height_mm: currentStage.height_mm,
      },
      { onSuccess: (r) => setResult(r) },
    );
  };

  const handleImport = () => {
    if (!result) return;
    onImported(result.canvas_data);
    reset();
    onClose();
  };

  const error = parse.error
    ? parse.error instanceof Error
      ? parse.error.message
      : String(parse.error)
    : null;

  // Overflow hint: content clearly larger than the label suggests the wrong
  // DPI (or a different label size).
  const overflow = result ? contentBounds(result.canvas_data) : null;
  const overflows =
    overflow != null &&
    (overflow.right > currentStage.width_mm * 1.05 ||
      overflow.bottom > currentStage.height_mm * 1.05);

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("zpl.importTitle")}
      footer={
        <>
          <Button variant="ghost" onClick={handleClose}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="secondary"
            onClick={handleAnalyze}
            disabled={parse.isPending || zpl.trim().length === 0}
          >
            {parse.isPending ? t("common.loading") : t("zpl.analyze")}
          </Button>
          <Button onClick={handleImport} disabled={result === null}>
            {t("zpl.importAction")}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-slate-400">{t("zpl.importHelp")}</p>
        <textarea
          value={zpl}
          onChange={(e) => onZplChange(e.target.value)}
          spellCheck={false}
          placeholder="^XA&#10;^FO50,50^A@N,28,28,E:ARI001.TTF^FD{NAZWA}^FS&#10;^XZ"
          className="h-48 w-full resize-y rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <div className="flex items-center gap-3">
          <div className="w-44">
            <Select
              label={t("zpl.dpi")}
              value={dpi}
              onChange={(e) => onDpiChange(e.target.value as DpiChoice)}
            >
              <option value="auto">{t("zpl.dpiAuto")}</option>
              <option value="203">203 dpi (8 dpmm)</option>
              <option value="300">300 dpi (12 dpmm)</option>
            </Select>
          </div>
          <p className="mt-5 text-xs text-amber-300">{t("zpl.importReplaceWarning")}</p>
        </div>

        {error && <p className="text-sm text-rose-400">{error}</p>}

        {result && (
          <div className="space-y-2 rounded border border-slate-700 bg-slate-950/60 p-2 text-xs">
            <p className="text-slate-300">
              {t("zpl.analyzed", {
                count: result.canvas_data.objects.length,
                dpi: result.detected_dpi ?? "?",
              })}
            </p>
            {overflows && (
              <p className="text-amber-300">
                {t("zpl.overflowHint", {
                  w: Math.round(overflow!.right),
                  h: Math.round(overflow!.bottom),
                  lw: currentStage.width_mm,
                  lh: currentStage.height_mm,
                })}
              </p>
            )}
            {result.warnings.length > 0 && (
              <ul className="max-h-20 overflow-auto text-amber-200">
                {result.warnings.map((w, i) => (
                  <li key={i}>• {w.message}</li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </Modal>
  );
}
