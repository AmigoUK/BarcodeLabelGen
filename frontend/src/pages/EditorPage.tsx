import { useEffect } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Canvas } from "../editor/Canvas";
import { LeftPanel } from "../editor/LeftPanel";
import { RightPanel } from "../editor/RightPanel";
import { Toolbar } from "../editor/Toolbar";
import { useEditorStore } from "../editor/store";
import { useTemplate, useUpdateTemplate } from "../hooks/useTemplates";

export function EditorPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const templateId = id ? Number(id) : null;

  const template = useTemplate(templateId);
  const update = useUpdateTemplate();

  const setCanvas = useEditorStore((s) => s.setCanvas);
  const markClean = useEditorStore((s) => s.markClean);
  const canvas = useEditorStore((s) => s.canvas);
  const dirty = useEditorStore((s) => s.dirty);
  const selectedId = useEditorStore((s) => s.selectedId);
  const deleteObject = useEditorStore((s) => s.deleteObject);

  // Hydrate the editor from the loaded template (once per template).
  useEffect(() => {
    if (template.data) {
      setCanvas(template.data.canvas_data);
    }
  }, [template.data, setCanvas]);

  // Keyboard: Delete key removes the selected object (when not typing).
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;
      if ((e.key === "Delete" || e.key === "Backspace") && selectedId) {
        e.preventDefault();
        deleteObject(selectedId);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, deleteObject]);

  // Warn before navigating away with unsaved changes.
  useEffect(() => {
    if (!dirty) return;
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      e.returnValue = "";
    };
    window.addEventListener("beforeunload", onBeforeUnload);
    return () => window.removeEventListener("beforeunload", onBeforeUnload);
  }, [dirty]);

  if (template.isLoading) {
    return <div className="p-6 text-slate-400">{t("common.loading")}</div>;
  }
  if (template.error || !template.data) {
    return <div className="p-6 text-rose-400">{t("editor.loadFailed")}</div>;
  }

  const handleSave = () => {
    if (!canvas || !templateId) return;
    update.mutate(
      { id: templateId, patch: { canvas_data: canvas } },
      { onSuccess: () => markClean() },
    );
  };

  return (
    <div className="flex h-screen flex-col bg-slate-950">
      <Toolbar
        template={template.data}
        onSave={handleSave}
        saving={update.isPending}
        saveError={
          update.error
            ? update.error instanceof Error
              ? update.error.message
              : String(update.error)
            : null
        }
      />
      <div className="flex min-h-0 flex-1">
        <LeftPanel />
        <div className="flex-1">
          <Canvas />
        </div>
        <RightPanel />
      </div>
    </div>
  );
}
