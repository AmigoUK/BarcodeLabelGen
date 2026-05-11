import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { Canvas } from "../editor/Canvas";
import { LeftPanel } from "../editor/LeftPanel";
import { RightPanel } from "../editor/RightPanel";
import { SeriesWizard } from "../editor/SeriesWizard";
import { Toolbar } from "../editor/Toolbar";
import { useEditorStore } from "../editor/store";
import type { CanvasData } from "../editor/types";
import { useAutosave } from "../editor/useAutosave";
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
  const undo = useEditorStore((s) => s.undo);
  const redo = useEditorStore((s) => s.redo);

  // Hydrate the editor ONCE per template — when the user navigates to a
  // different template id. Re-hydrating after every save would clobber any
  // edits the user made while the save request was in flight.
  const loadedTemplateRef = useRef<number | null>(null);
  useEffect(() => {
    if (template.data && loadedTemplateRef.current !== template.data.id) {
      setCanvas(template.data.canvas_data);
      loadedTemplateRef.current = template.data.id;
    }
  }, [template.data, setCanvas]);

  // Save fn shared by manual button + autosave + Ctrl+S.
  // Only marks the editor clean if the user hasn't made further edits while
  // the request was in flight — otherwise dirty stays true and the next
  // autosave/Save picks up the newer canvas.
  const saveCanvas = useCallback(
    async (c: CanvasData) => {
      if (!templateId) return;
      await update.mutateAsync({ id: templateId, patch: { canvas_data: c } });
      if (useEditorStore.getState().canvas === c) {
        markClean();
      }
    },
    [templateId, update, markClean],
  );

  // Autosave 30s after the last edit.
  const autosave = useAutosave(canvas, dirty, saveCanvas, 30_000);

  // Keyboard shortcuts — suppressed while typing in inputs.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;

      const mod = e.ctrlKey || e.metaKey;

      if ((e.key === "Delete" || e.key === "Backspace") && selectedId) {
        e.preventDefault();
        deleteObject(selectedId);
      } else if (mod && e.key.toLowerCase() === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if (
        (mod && e.key.toLowerCase() === "y") ||
        (mod && e.shiftKey && e.key.toLowerCase() === "z")
      ) {
        e.preventDefault();
        redo();
      } else if (mod && e.key.toLowerCase() === "s") {
        e.preventDefault();
        if (canvas) void saveCanvas(canvas);
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [selectedId, deleteObject, undo, redo, canvas, saveCanvas]);

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

  const [showWizard, setShowWizard] = useState(false);

  if (template.isLoading) {
    return <div className="p-6 text-slate-400">{t("common.loading")}</div>;
  }
  if (template.error || !template.data) {
    return <div className="p-6 text-rose-400">{t("editor.loadFailed")}</div>;
  }

  return (
    <div className="flex h-screen flex-col bg-slate-950">
      <Toolbar
        template={template.data}
        onSave={() => canvas && void saveCanvas(canvas)}
        saving={update.isPending}
        saveError={
          update.error
            ? update.error instanceof Error
              ? update.error.message
              : String(update.error)
            : null
        }
        autosaveStatus={autosave.status}
        autosaveAt={autosave.lastSavedAt}
        onGenerateSeries={() => setShowWizard(true)}
        seriesDisabled={dirty}
      />
      <div className="flex min-h-0 flex-1">
        <LeftPanel />
        <Canvas />
        <RightPanel />
      </div>
      {showWizard && canvas && (
        <SeriesWizard
          templateId={template.data.id}
          templateName={template.data.name}
          canvas={canvas}
          onClose={() => setShowWizard(false)}
        />
      )}
    </div>
  );
}
