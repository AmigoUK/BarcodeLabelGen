import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
import { Button } from "../components/ui/Button";
import type { TemplateDetail } from "../hooks/useTemplates";
import { useEditorStore } from "./store";

type Props = {
  template: TemplateDetail;
  onSave: () => void;
  saving: boolean;
  saveError?: string | null;
  autosaveStatus: "idle" | "saving" | "saved" | "error";
  autosaveAt: Date | null;
};

export function Toolbar({
  template,
  onSave,
  saving,
  saveError,
  autosaveStatus,
  autosaveAt,
}: Props) {
  const { t } = useTranslation();
  const dirty = useEditorStore((s) => s.dirty);
  const past = useEditorStore((s) => s.past.length);
  const future = useEditorStore((s) => s.future.length);
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);

  const autosaveLabel = (() => {
    if (autosaveStatus === "saving") return t("editor.autosaving");
    if (autosaveStatus === "saved" && autosaveAt) {
      return t("editor.autosavedAt", {
        time: autosaveAt.toLocaleTimeString(),
      });
    }
    return null;
  })();

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
        {saveError && <span className="ml-2 text-xs text-rose-400">{saveError}</span>}
        <Button onClick={onSave} disabled={saving || !dirty} className="ml-2">
          {saving ? t("common.loading") : t("editor.save") + " (Ctrl+S)"}
        </Button>
      </div>
    </div>
  );
}
