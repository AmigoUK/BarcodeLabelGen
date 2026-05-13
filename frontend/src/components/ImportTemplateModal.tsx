/**
 * Three-phase modal for importing a `.blg-template.json` file:
 *   1. Upload — pick a file, read it client-side, ship to /preview.
 *   2. Configure — name + size override, object checklist, per-duplicate
 *      reuse/copy radios, surfaced warnings.
 *   3. Submit — POST /import with options, navigate to the new template.
 */

import { useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import {
  type ImportOptions,
  type ImportPreview,
  type ObjectSummary,
  useImportTemplate,
  usePreviewImport,
} from "../hooks/useTemplates";
import { ApiError } from "../lib/api";
import { Button } from "./ui/Button";
import { Input } from "./ui/Input";
import { Modal } from "./ui/Modal";

type Props = { onClose: () => void };

function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === "string" && err.detail.length > 0) return err.detail;
    return err.code;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

export function ImportTemplateModal({ onClose }: Props) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const previewMut = usePreviewImport();
  const importMut = useImportTemplate();

  const fileRef = useRef<HTMLInputElement>(null);
  const [source, setSource] = useState<unknown>(null);
  const [preview, setPreview] = useState<ImportPreview | null>(null);
  const [parseError, setParseError] = useState<string | null>(null);

  // Phase-2 form state
  const [nameOverride, setNameOverride] = useState("");
  const [widthOverride, setWidthOverride] = useState<number | "">("");
  const [heightOverride, setHeightOverride] = useState<number | "">("");
  const [skipped, setSkipped] = useState<Set<string>>(new Set());
  const [resolutions, setResolutions] = useState<Record<string, "reuse" | "new">>({});

  const onFile = async (file: File) => {
    setParseError(null);
    let parsed: unknown;
    try {
      const text = await file.text();
      parsed = JSON.parse(text);
    } catch {
      setParseError(t("templates.importErrorBadFile"));
      return;
    }
    try {
      const res = await previewMut.mutateAsync(parsed);
      setSource(parsed);
      setPreview(res);
      setNameOverride(res.template_name);
      setWidthOverride(res.width_mm);
      setHeightOverride(res.height_mm);
      // Default per-duplicate decision: reuse (cheaper, expected behaviour).
      const defaults: Record<string, "reuse" | "new"> = {};
      for (const d of res.asset_duplicates) {
        if (d.matches_existing) defaults[d.ref] = "reuse";
      }
      setResolutions(defaults);
      setSkipped(new Set());
    } catch (err) {
      setParseError(describeError(err));
    }
  };

  const toggleSkip = (id: string) => {
    setSkipped((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const submit = async () => {
    if (!source || !preview) return;
    const opts: ImportOptions = {};
    if (nameOverride && nameOverride !== preview.template_name) opts.name = nameOverride;
    if (typeof widthOverride === "number" && widthOverride !== preview.width_mm)
      opts.width_mm = widthOverride;
    if (typeof heightOverride === "number" && heightOverride !== preview.height_mm)
      opts.height_mm = heightOverride;
    if (skipped.size > 0) opts.skip_object_ids = Array.from(skipped);
    if (Object.keys(resolutions).length > 0) opts.asset_resolution = resolutions;

    try {
      const created = await importMut.mutateAsync({ source, options: opts });
      onClose();
      void navigate(`/templates/${created.id}/edit`);
    } catch {
      /* error rendered below from importMut.error */
    }
  };

  const phase: "upload" | "configure" = preview ? "configure" : "upload";

  return (
    <Modal
      open
      onClose={onClose}
      title={t("templates.importTitle")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          {phase === "configure" && (
            <Button onClick={() => void submit()} disabled={importMut.isPending}>
              {importMut.isPending ? t("common.loading") : t("templates.importSubmit")}
            </Button>
          )}
        </>
      }
    >
      {phase === "upload" && (
        <UploadPhase
          onPick={() => fileRef.current?.click()}
          loading={previewMut.isPending}
          parseError={parseError}
        />
      )}

      {phase === "configure" && preview && (
        <ConfigurePhase
          preview={preview}
          nameOverride={nameOverride}
          setNameOverride={setNameOverride}
          widthOverride={widthOverride}
          setWidthOverride={setWidthOverride}
          heightOverride={heightOverride}
          setHeightOverride={setHeightOverride}
          skipped={skipped}
          toggleSkip={toggleSkip}
          resolutions={resolutions}
          setResolutions={setResolutions}
          submitError={importMut.error ? describeError(importMut.error) : null}
        />
      )}

      <input
        ref={fileRef}
        type="file"
        accept=".json,.blg-template.json,application/json"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onFile(f);
          e.target.value = "";
        }}
      />
    </Modal>
  );
}

function UploadPhase({
  onPick,
  loading,
  parseError,
}: {
  onPick: () => void;
  loading: boolean;
  parseError: string | null;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-300">{t("templates.importStep1")}</p>
      <Button variant="secondary" onClick={onPick} disabled={loading}>
        {loading ? t("common.loading") : t("templates.importPickFile")}
      </Button>
      {parseError && (
        <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {parseError}
        </p>
      )}
    </div>
  );
}

function ConfigurePhase({
  preview,
  nameOverride,
  setNameOverride,
  widthOverride,
  setWidthOverride,
  heightOverride,
  setHeightOverride,
  skipped,
  toggleSkip,
  resolutions,
  setResolutions,
  submitError,
}: {
  preview: ImportPreview;
  nameOverride: string;
  setNameOverride: (v: string) => void;
  widthOverride: number | "";
  setWidthOverride: (v: number | "") => void;
  heightOverride: number | "";
  setHeightOverride: (v: number | "") => void;
  skipped: Set<string>;
  toggleSkip: (id: string) => void;
  resolutions: Record<string, "reuse" | "new">;
  setResolutions: (r: Record<string, "reuse" | "new">) => void;
  submitError: string | null;
}) {
  const { t } = useTranslation();
  const duplicates = useMemo(
    () => preview.asset_duplicates.filter((d) => d.matches_existing),
    [preview.asset_duplicates],
  );

  return (
    <div className="space-y-4">
      <p className="text-sm text-slate-300">{t("templates.importStep2")}</p>

      <Input
        label={t("templates.importOverrideName")}
        value={nameOverride}
        onChange={(e) => setNameOverride(e.target.value)}
      />

      <div>
        <label className="mb-1 block text-sm font-medium text-slate-200">
          {t("templates.importOverrideSize")}
        </label>
        <div className="grid grid-cols-2 gap-2">
          <Input
            type="number"
            min={10}
            max={1000}
            step={1}
            value={widthOverride}
            onChange={(e) => setWidthOverride(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder={t("templates.customWidthMm")}
          />
          <Input
            type="number"
            min={10}
            max={1000}
            step={1}
            value={heightOverride}
            onChange={(e) => setHeightOverride(e.target.value === "" ? "" : Number(e.target.value))}
            placeholder={t("templates.customHeightMm")}
          />
        </div>
      </div>

      <div>
        <label className="mb-2 block text-sm font-medium text-slate-200">
          {t("templates.importObjects")}
        </label>
        <div className="max-h-48 space-y-1 overflow-y-auto rounded border border-slate-800 bg-slate-950/30 p-2">
          {preview.object_summary.map((obj) => (
            <ObjectRow key={obj.id} obj={obj} skipped={skipped.has(obj.id)} onToggle={toggleSkip} />
          ))}
        </div>
      </div>

      {duplicates.length > 0 && (
        <div>
          <label className="mb-2 block text-sm font-medium text-slate-200">
            {t("templates.importDuplicates")}
          </label>
          <div className="space-y-2 rounded border border-slate-800 bg-slate-950/30 p-3">
            {duplicates.map((d) => (
              <div key={d.ref} className="text-sm">
                <p className="text-slate-300">
                  <span className="font-mono text-xs text-slate-500">{d.ref}</span>{" "}
                  {t("templates.importDupAlreadyAs", { name: d.existing_filename ?? "?" })}
                </p>
                <div className="mt-1 flex gap-3 text-xs">
                  <label className="flex items-center gap-1 text-slate-300">
                    <input
                      type="radio"
                      name={`res-${d.ref}`}
                      checked={(resolutions[d.ref] ?? "reuse") === "reuse"}
                      onChange={() => setResolutions({ ...resolutions, [d.ref]: "reuse" })}
                    />
                    {t("templates.importDupReuseExisting")}
                  </label>
                  <label className="flex items-center gap-1 text-slate-300">
                    <input
                      type="radio"
                      name={`res-${d.ref}`}
                      checked={resolutions[d.ref] === "new"}
                      onChange={() => setResolutions({ ...resolutions, [d.ref]: "new" })}
                    />
                    {t("templates.importDupCreateNew")}
                  </label>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {preview.warnings.length > 0 && (
        <div className="rounded border border-amber-900 bg-amber-950/40 p-3">
          <p className="text-sm font-medium text-amber-200">{t("templates.importWarnings")}</p>
          <ul className="mt-1 list-disc pl-5 text-xs text-amber-300">
            {preview.warnings.map((w, i) => (
              <li key={i}>{w}</li>
            ))}
          </ul>
        </div>
      )}

      {submitError && (
        <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {submitError}
        </p>
      )}
    </div>
  );
}

function ObjectRow({
  obj,
  skipped,
  onToggle,
}: {
  obj: ObjectSummary;
  skipped: boolean;
  onToggle: (id: string) => void;
}) {
  const icon = ICONS[obj.type] ?? "•";
  return (
    <label className="flex items-center gap-2 rounded px-2 py-1 text-sm text-slate-200 hover:bg-slate-900">
      <input
        type="checkbox"
        checked={!skipped}
        onChange={() => onToggle(obj.id)}
        className="h-4 w-4 rounded border-slate-700 bg-slate-900"
      />
      <span className="w-5 text-slate-500">{icon}</span>
      <span className="truncate">{obj.label}</span>
      {obj.has_dynamic && (
        <span className="ml-auto rounded bg-indigo-900/50 px-1.5 py-0.5 text-[10px] text-indigo-200">
          {"{{…}}"}
        </span>
      )}
    </label>
  );
}

const ICONS: Record<string, string> = {
  text: "T",
  rect: "▭",
  line: "╱",
  image: "🖼",
  barcode: "▤",
};
