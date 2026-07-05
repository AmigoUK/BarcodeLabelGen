import { useCallback, useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useParams } from "react-router-dom";
import { AppFooter } from "../components/AppFooter";
import { AlignmentBar } from "../editor/AlignmentBar";
import { Canvas } from "../editor/Canvas";
import { ExportTsplModal } from "../editor/ExportTsplModal";
import { ExportZplModal } from "../editor/ExportZplModal";
import { ImportZplModal } from "../editor/ImportZplModal";
import { PrintModal } from "../editor/PrintModal";
import { PrintPreviewModal } from "../editor/PrintPreviewModal";
import { VersionHistoryModal } from "../editor/VersionHistoryModal";
import { LabelSettingsModal } from "../editor/LabelSettingsModal";
import { LeftPanel } from "../editor/LeftPanel";
import { RightPanel } from "../editor/RightPanel";
import { SeriesWizard } from "../editor/SeriesWizard";
import { Toolbar } from "../editor/Toolbar";
import { useEditorStore } from "../editor/store";
import type { CanvasData } from "../editor/types";
import { useAutosave } from "../editor/useAutosave";
import { type PdfWarning, useGeneratePdf } from "../hooks/useGeneratePdf";
import { useTemplate, useUpdateTemplate } from "../hooks/useTemplates";

export function EditorPage() {
  const { t } = useTranslation();
  const { id } = useParams<{ id: string }>();
  const templateId = id ? Number(id) : null;

  const template = useTemplate(templateId);
  const update = useUpdateTemplate();

  const setCanvas = useEditorStore((s) => s.setCanvas);
  const replaceCanvas = useEditorStore((s) => s.replaceCanvas);
  const setStageSize = useEditorStore((s) => s.setStageSize);
  const markClean = useEditorStore((s) => s.markClean);
  const canvas = useEditorStore((s) => s.canvas);
  const dirty = useEditorStore((s) => s.dirty);
  const selectedIds = useEditorStore((s) => s.selectedIds);
  const deleteObject = useEditorStore((s) => s.deleteObject);
  const selectMany = useEditorStore((s) => s.selectMany);
  const clearSelection = useEditorStore((s) => s.clearSelection);
  const duplicateSelected = useEditorStore((s) => s.duplicateSelected);
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
    // `snapshot` distinguishes a deliberate save (button / Ctrl+S) from an
    // autosave — only the former records a version in the history (F17).
    async (c: CanvasData, opts?: { snapshot?: boolean }) => {
      if (!templateId) return;
      // Persist the label dimensions alongside the canvas so the template
      // record (used by PDF/ZPL generation) stays in sync with the stage the
      // user sees — e.g. after editing the label size.
      await update.mutateAsync({
        id: templateId,
        patch: {
          canvas_data: c,
          width_mm: c.stage.width_mm,
          height_mm: c.stage.height_mm,
          snapshot: opts?.snapshot ?? false,
        },
      });
      if (useEditorStore.getState().canvas === c) {
        markClean();
      }
    },
    [templateId, update, markClean],
  );

  // Autosave 30s after the last edit — never snapshots.
  const autosave = useAutosave(canvas, dirty, saveCanvas, 30_000);

  // Keyboard shortcuts — suppressed while typing in inputs.
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const target = e.target as HTMLElement | null;
      const tag = target?.tagName.toLowerCase();
      if (tag === "input" || tag === "textarea" || target?.isContentEditable) return;

      const mod = e.ctrlKey || e.metaKey;

      if ((e.key === "Delete" || e.key === "Backspace") && selectedIds.length > 0) {
        e.preventDefault();
        // Delete every selected object — store removes them from
        // selectedIds as it goes, but copying first avoids shifting
        // the array while we iterate.
        for (const id of [...selectedIds]) deleteObject(id);
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
        if (canvas) void saveCanvas(canvas, { snapshot: true });
      } else if (mod && e.key.toLowerCase() === "d" && !e.shiftKey) {
        // Ctrl/Cmd+D — duplicate selection in place with a small offset so
        // the clones don't overlap the originals. preventDefault stops the
        // browser's "bookmark this page" handler.
        e.preventDefault();
        if (selectedIds.length > 0) duplicateSelected({ dx: 5, dy: 5 });
      } else if (mod && e.key.toLowerCase() === "a") {
        // Ctrl/Cmd+A — select all objects on the canvas. Skips when
        // there's nothing to select so the browser default doesn't fire
        // either ("select all text on the page" would be jarring here).
        if (canvas && canvas.objects.length > 0) {
          e.preventDefault();
          selectMany(canvas.objects.map((o) => o.id));
        }
      } else if (e.key === "Escape") {
        if (selectedIds.length > 0) {
          e.preventDefault();
          clearSelection();
        }
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [
    selectedIds,
    deleteObject,
    duplicateSelected,
    undo,
    redo,
    canvas,
    saveCanvas,
    selectMany,
    clearSelection,
  ]);

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
  const [showImportZpl, setShowImportZpl] = useState(false);
  const [showExportZpl, setShowExportZpl] = useState(false);
  const [showExportTspl, setShowExportTspl] = useState(false);
  const [showLabelSize, setShowLabelSize] = useState(false);
  const [showPrint, setShowPrint] = useState(false);
  const [showHistory, setShowHistory] = useState(false);
  const generatePreview = useGeneratePdf();
  const [preview, setPreview] = useState<{ blob: Blob; warnings: PdfWarning[] } | null>(null);

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
        onSave={() => canvas && void saveCanvas(canvas, { snapshot: true })}
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
        onImportZpl={() => setShowImportZpl(true)}
        onExportZpl={() => setShowExportZpl(true)}
        onExportTspl={() => setShowExportTspl(true)}
        onLabelSize={() => setShowLabelSize(true)}
        onPrint={() => setShowPrint(true)}
        onHistory={() => setShowHistory(true)}
        onPreview={() => {
          generatePreview.mutate(
            { templateId: template.data.id },
            { onSuccess: (res) => setPreview({ blob: res.blob, warnings: res.warnings }) },
          );
        }}
      />
      <AlignmentBar />
      <div className="flex min-h-0 flex-1">
        <LeftPanel />
        <Canvas />
        <RightPanel />
      </div>
      <AppFooter />
      {showWizard && canvas && (
        <SeriesWizard
          templateId={template.data.id}
          templateName={template.data.name}
          canvas={canvas}
          onClose={() => setShowWizard(false)}
        />
      )}
      {canvas && (
        <>
          <ImportZplModal
            open={showImportZpl}
            onClose={() => setShowImportZpl(false)}
            currentStage={canvas.stage}
            onImported={(parsed) => replaceCanvas(keepCurrentLabelSize(parsed))}
          />
          <ExportZplModal
            open={showExportZpl}
            onClose={() => setShowExportZpl(false)}
            canvas={canvas}
            templateId={template.data.id}
            templateName={template.data.name}
          />
          <ExportTsplModal
            open={showExportTspl}
            onClose={() => setShowExportTspl(false)}
            canvas={canvas}
            templateName={template.data.name}
          />
          <LabelSettingsModal
            open={showLabelSize}
            onClose={() => setShowLabelSize(false)}
            widthMm={canvas.stage.width_mm}
            heightMm={canvas.stage.height_mm}
            onApply={(w, h) => setStageSize(w, h)}
          />
          <PrintModal open={showPrint} onClose={() => setShowPrint(false)} canvas={canvas} />
          {showHistory && (
            <VersionHistoryModal
              templateId={template.data.id}
              onClose={() => setShowHistory(false)}
              onRestored={(restored) => replaceCanvas(restored.canvas_data)}
            />
          )}
          {preview && (
            <PrintPreviewModal
              blob={preview.blob}
              warnings={preview.warnings}
              filename={`${template.data.name.replace(/[^A-Za-z0-9._-]+/g, "_") || "label"}.pdf`}
              onClose={() => setPreview(null)}
            />
          )}
        </>
      )}
    </div>
  );
}

/** ZPL import brings in elements, not a new label format: keep the label
 *  size the user already set. We overwrite the parsed stage dimensions with
 *  the current ones and drop the imported ^PW/^LL so a later ZPL export
 *  matches the size shown on screen. */
function keepCurrentLabelSize(parsed: CanvasData): CanvasData {
  const current = useEditorStore.getState().canvas;
  if (!current) return parsed;
  const nextZpl = { ...(parsed.stage.zpl ?? {}) };
  delete nextZpl.pw;
  delete nextZpl.ll;
  return {
    ...parsed,
    stage: {
      ...parsed.stage,
      width_mm: current.stage.width_mm,
      height_mm: current.stage.height_mm,
      zpl: nextZpl,
    },
  };
}
