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
};

export function Toolbar({ template, onSave, saving, saveError }: Props) {
  const { t } = useTranslation();
  const dirty = useEditorStore((s) => s.dirty);

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
      </div>
      <div className="flex items-center gap-3">
        {saveError && <span className="text-xs text-rose-400">{saveError}</span>}
        <Button onClick={onSave} disabled={saving || !dirty}>
          {saving ? t("common.loading") : t("editor.save")}
        </Button>
      </div>
    </div>
  );
}
