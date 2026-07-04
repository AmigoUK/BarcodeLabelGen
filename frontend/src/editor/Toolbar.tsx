import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { downloadPdfBlob, useGeneratePdf } from "../hooks/useGeneratePdf";
import { type TemplateDetail, exportTemplateToFile } from "../hooks/useTemplates";
import { useEditorStore } from "./store";

type Props = {
  template: TemplateDetail;
  onSave: () => void;
  saving: boolean;
  saveError?: string | null;
  autosaveStatus: "idle" | "saving" | "saved" | "error";
  autosaveAt: Date | null;
  onGenerateSeries: () => void;
  /** Disable the series button while there are unsaved changes — series
   * generation always uses the last-saved canvas, so the user should save
   * first to avoid generating from stale data. */
  seriesDisabled: boolean;
  onImportZpl: () => void;
  onExportZpl: () => void;
  onLabelSize: () => void;
  onPrint: () => void;
  onHistory: () => void;
  onPreview: () => void;
};

export function Toolbar({
  template,
  onSave,
  saving,
  saveError,
  autosaveStatus,
  autosaveAt,
  onGenerateSeries,
  seriesDisabled,
  onImportZpl,
  onExportZpl,
  onLabelSize,
  onPrint,
  onHistory,
  onPreview,
}: Props) {
  const { t } = useTranslation();
  const dirty = useEditorStore((s) => s.dirty);
  const past = useEditorStore((s) => s.past.length);
  const future = useEditorStore((s) => s.future.length);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);
  const stage = useEditorStore((s) => s.canvas?.stage);
  const generate = useGeneratePdf();

  const autosaveLabel = (() => {
    if (autosaveStatus === "saving") return t("editor.autosaving");
    if (autosaveStatus === "saved" && autosaveAt) {
      return t("editor.autosavedAt", { time: autosaveAt.toLocaleTimeString() });
    }
    return null;
  })();

  const generateError = generate.error
    ? generate.error instanceof Error
      ? generate.error.message
      : String(generate.error)
    : null;

  return (
    <div className="flex items-center justify-between gap-3 border-b border-slate-800 bg-slate-950 px-4 py-2">
      <div className="flex items-center gap-3">
        <Link to="/templates" className="text-sm text-slate-400 hover:text-slate-100">
          ← {t("nav.templates")}
        </Link>
        <span className="text-slate-700">|</span>
        <h2 className="text-sm font-semibold text-slate-100">{template.name}</h2>
        <span className="text-xs text-slate-500">v{template.version}</span>
        {dirty && (
          <span className="rounded bg-amber-900/40 px-2 py-0.5 text-xs text-amber-300">
            {t("editor.unsaved")}
          </span>
        )}
        {autosaveLabel && <span className="text-xs text-slate-500">{autosaveLabel}</span>}
      </div>
      <div className="flex items-center gap-1">
        <Button
          variant="ghost"
          onClick={undo}
          disabled={past === 0}
          title={t("editor.undo") + " (Ctrl+Z)"}
        >
          ↶
        </Button>
        <Button
          variant="ghost"
          onClick={redo}
          disabled={future === 0}
          title={t("editor.redo") + " (Ctrl+Y)"}
        >
          ↷
        </Button>
        {generateError && (
          <span className="ml-2 text-xs text-rose-400" title={generateError}>
            {t("editor.pdfFailed")}
          </span>
        )}
        {generate.data && generate.data.warnings.length > 0 && (
          <span
            className="ml-2 cursor-help rounded bg-amber-900/40 px-2 py-0.5 text-xs text-amber-300"
            title={
              t("editor.pdfWarningsTooltip") +
              "\n" +
              generate.data.warnings.map((w) => `• ${w.object_id}: ${w.message}`).join("\n")
            }
          >
            ⚠ {t("editor.pdfWarnings", { count: generate.data.warnings.length })}
          </span>
        )}
        <Button
          variant="secondary"
          className="ml-2"
          onClick={onGenerateSeries}
          disabled={seriesDisabled}
          title={seriesDisabled ? t("editor.saveFirstHint") : ""}
        >
          {t("editor.generateSeries")}
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            const safeName = template.name.replace(/[^A-Za-z0-9._-]+/g, "_");
            void exportTemplateToFile(template.id, `${safeName}.blg-template.json`);
          }}
          title={t("templates.exportTooltip")}
        >
          ⬇ {t("templates.export")}
        </Button>
        <Button variant="ghost" onClick={onLabelSize} title={t("labelSize.tooltip")}>
          {stage ? `📐 ${stage.width_mm}×${stage.height_mm}` : t("labelSize.title")}
        </Button>
        <Button variant="ghost" onClick={onImportZpl} title={t("zpl.importTooltip")}>
          {t("zpl.import")}
        </Button>
        <Button variant="ghost" onClick={onExportZpl} title={t("zpl.exportTooltip")}>
          {t("zpl.export")}
        </Button>
        <Button variant="ghost" onClick={onPrint} title={t("print.tooltip")}>
          🖨 {t("print.button")}
        </Button>
        <Button variant="ghost" onClick={onHistory} title={t("history.tooltip")}>
          🕘 {t("history.button")}
        </Button>
        <Button variant="ghost" onClick={onPreview} title={t("preview.tooltip")}>
          👁 {t("preview.button")}
        </Button>
        <Button
          variant="secondary"
          onClick={() => {
            const safeName = template.name.replace(/[^A-Za-z0-9._-]+/g, "_");
            generate.mutate(
              { templateId: template.id },
              { onSuccess: (res) => downloadPdfBlob(res.blob, `${safeName}.pdf`) },
            );
          }}
          disabled={generate.isPending}
        >
          {generate.isPending ? t("editor.generatingPdf") : t("editor.downloadPdf")}
        </Button>
        {saveError && <span className="ml-2 text-xs text-rose-400">{saveError}</span>}
        <Button onClick={onSave} disabled={saving || !dirty}>
          {saving ? t("common.loading") : t("editor.save") + " (Ctrl+S)"}
        </Button>
      </div>
    </div>
  );
}
