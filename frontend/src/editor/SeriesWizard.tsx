/**
 * 4-step mail-merge wizard. Opens from the editor toolbar's "Generate
 * Series" button. Walks the user through:
 *   1. Upload XLS/CSV
 *   2. Map detected placeholders to CSV columns
 *   3. Optional filter (column op value) with live match count
 *   4. Submit batch job, poll progress, download PDF
 */

import { useEffect, useMemo, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import {
  type DataSet,
  type FilterOp,
  type FilterSpec,
  type SqliteTableInfo,
  downloadJobPdf,
  useConfigureSqlite,
  useFilterDataset,
  useJobStatus,
  useSubmitBatch,
  useUploadDataset,
} from "../hooks/useDatasets";
import { ApiError } from "../lib/api";
import { evaluateDatePlaceholder, isPlainDateKey } from "../lib/datePlaceholder";
import type { CanvasData } from "./types";

/** Pull the most useful human-readable string out of an unknown thrown value.
 *  ApiError carries server-side `detail` which the bare `.message` would hide. */
function describeError(err: unknown): string {
  if (err instanceof ApiError) {
    if (typeof err.detail === "string" && err.detail.length > 0) return err.detail;
    return err.code;
  }
  if (err instanceof Error) return err.message;
  return String(err);
}

type Props = {
  templateId: number;
  templateName: string;
  canvas: CanvasData;
  onClose: () => void;
};

const PLACEHOLDER_RE = /\{\{\s*([^}]+?)\s*\}\}/g;
const FILTER_OPS: FilterOp[] = ["eq", "neq", "contains", "gt", "lt", "empty", "non_empty"];

function detectTemplatePlaceholders(canvas: CanvasData): string[] {
  const out = new Set<string>();
  for (const obj of canvas.objects) {
    const text = obj.type === "text" ? obj.text : obj.type === "barcode" ? obj.data : "";
    let m: RegExpExecArray | null;
    PLACEHOLDER_RE.lastIndex = 0;
    while ((m = PLACEHOLDER_RE.exec(text)) !== null) {
      const key = m[1].trim();
      // Computed date forms ({{date+14d}}, {{date:YYYY-MM-DD}}) never map
      // to a column; only the bare {{date}} may be shadowed by one.
      if (evaluateDatePlaceholder(key) !== null && !isPlainDateKey(key)) continue;
      out.add(key);
    }
  }
  return Array.from(out);
}

type Step = "upload" | "map" | "filter" | "generate";

export function SeriesWizard({ templateId, templateName, canvas, onClose }: Props) {
  const { t } = useTranslation();
  const placeholders = useMemo(() => detectTemplatePlaceholders(canvas), [canvas]);

  const [step, setStep] = useState<Step>("upload");
  const [dataset, setDataset] = useState<DataSet | null>(null);
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [filterEnabled, setFilterEnabled] = useState(false);
  const [filter, setFilter] = useState<FilterSpec>({
    column: "",
    op: "eq",
    value: "",
  });
  const [jobId, setJobId] = useState<string | null>(null);

  const upload = useUploadDataset();
  const configureSqlite = useConfigureSqlite();
  const filterMutation = useFilterDataset();
  const submit = useSubmitBatch();
  const jobQuery = useJobStatus(jobId);

  useEffect(() => {
    if (!dataset) return;
    const auto: Record<string, string> = {};
    for (const ph of placeholders) {
      if (dataset.columns.includes(ph)) auto[ph] = ph;
    }
    setMapping(auto);
  }, [dataset, placeholders]);

  const downloadedRef = useRef(false);
  useEffect(() => {
    if (jobQuery.data?.status === "done" && jobId && !downloadedRef.current) {
      downloadedRef.current = true;
      const safe = templateName.replace(/[^A-Za-z0-9._-]+/g, "_") || "labels";
      void downloadJobPdf(jobId, `${safe}_${jobQuery.data.total}.pdf`);
    }
  }, [jobQuery.data, jobId, templateName]);

  // SQLite uploads start unconfigured (no columns yet) — must run PATCH /sqlite-config
  // before the mapping step has anything to map onto.
  const isSqliteUnconfigured =
    dataset !== null && dataset.source_type === "sqlite" && dataset.columns.length === 0;
  const canAdvanceFromUpload = dataset !== null && !isSqliteUnconfigured;
  // Bare {{date}} needs no mapping — the backend fills in today's date.
  const canAdvanceFromMap = placeholders.every((ph) => mapping[ph] || isPlainDateKey(ph));

  return (
    <Modal open onClose={onClose} title={`${t("series.title")} - ${templateName}`} footer={null}>
      <Steps current={step} />

      {step === "upload" && (
        <UploadStep
          dataset={dataset}
          uploadError={upload.error ? describeError(upload.error) : null}
          uploading={upload.isPending}
          onFile={async (file) => {
            try {
              const ds = await upload.mutateAsync(file);
              setDataset(ds);
            } catch {
              /* error surfaced via uploadError */
            }
          }}
          configuring={configureSqlite.isPending}
          configureError={configureSqlite.error ? describeError(configureSqlite.error) : null}
          onConfigureSqlite={async (input) => {
            try {
              const updated = await configureSqlite.mutateAsync(input);
              // Preserve the upload-only `sqlite_tables` field for re-config UX.
              setDataset((prev) =>
                prev ? { ...updated, sqlite_tables: prev.sqlite_tables } : updated,
              );
            } catch {
              /* error surfaced via configureError */
            }
          }}
        />
      )}

      {step === "map" && dataset && (
        <MapStep
          placeholders={placeholders}
          columns={dataset.columns}
          mapping={mapping}
          onChange={setMapping}
        />
      )}

      {step === "filter" && dataset && (
        <FilterStep
          dataset={dataset}
          enabled={filterEnabled}
          filter={filter}
          onEnable={setFilterEnabled}
          onChange={setFilter}
          matchCount={filterMutation.data?.match_count ?? null}
          onTest={() => filterMutation.mutate({ datasetId: dataset.id, filter })}
          testing={filterMutation.isPending}
        />
      )}

      {step === "generate" && dataset && (
        <GenerateStep
          dataset={dataset}
          mapping={mapping}
          filter={filterEnabled ? filter : null}
          job={jobQuery.data ?? null}
          submitting={submit.isPending}
          submitError={submit.error ? describeError(submit.error) : null}
          onSubmit={async () => {
            const res = await submit.mutateAsync({
              template_id: templateId,
              dataset_id: dataset.id,
              mapping,
              filter: filterEnabled ? filter : undefined,
            });
            downloadedRef.current = false;
            setJobId(res.job_id);
          }}
        />
      )}

      <div className="mt-5 flex justify-between gap-2 border-t border-slate-800 pt-3">
        <Button variant="secondary" onClick={onClose}>
          {t("common.close")}
        </Button>
        <div className="flex gap-2">
          {step !== "upload" && (
            <Button
              variant="secondary"
              onClick={() => {
                if (step === "map") setStep("upload");
                else if (step === "filter") setStep("map");
                else if (step === "generate") setStep("filter");
              }}
              disabled={jobQuery.data?.status === "running"}
            >
              {t("series.back")}
            </Button>
          )}
          {step !== "generate" && (
            <Button
              onClick={() => {
                if (step === "upload" && canAdvanceFromUpload) setStep("map");
                else if (step === "map" && canAdvanceFromMap) setStep("filter");
                else if (step === "filter") setStep("generate");
              }}
              disabled={
                (step === "upload" && !canAdvanceFromUpload) ||
                (step === "map" && !canAdvanceFromMap)
              }
            >
              {t("series.next")}
            </Button>
          )}
        </div>
      </div>
    </Modal>
  );
}

function Steps({ current }: { current: Step }) {
  const { t } = useTranslation();
  const items: { key: Step; label: string }[] = [
    { key: "upload", label: t("series.step1") },
    { key: "map", label: t("series.step2") },
    { key: "filter", label: t("series.step3") },
    { key: "generate", label: t("series.step4") },
  ];
  return (
    <ol className="mb-5 flex items-center justify-between gap-1 text-xs">
      {items.map((it, i) => {
        const isActive = it.key === current;
        return (
          <li
            key={it.key}
            className={[
              "flex flex-1 items-center gap-2 rounded px-2 py-1.5",
              isActive ? "bg-indigo-900/40 text-indigo-200" : "text-slate-400",
            ].join(" ")}
          >
            <span
              className={[
                "flex h-5 w-5 items-center justify-center rounded-full text-[10px] font-bold",
                isActive ? "bg-indigo-600 text-white" : "bg-slate-800 text-slate-400",
              ].join(" ")}
            >
              {i + 1}
            </span>
            <span className="truncate">{it.label}</span>
          </li>
        );
      })}
    </ol>
  );
}

function UploadStep({
  dataset,
  uploadError,
  uploading,
  onFile,
  configuring,
  configureError,
  onConfigureSqlite,
}: {
  dataset: DataSet | null;
  uploadError: string | null;
  uploading: boolean;
  onFile: (f: File) => Promise<void>;
  configuring: boolean;
  configureError: string | null;
  onConfigureSqlite: (input: {
    datasetId: number;
    table?: string;
    query?: string;
  }) => Promise<void>;
}) {
  const { t } = useTranslation();
  const fileRef = useRef<HTMLInputElement>(null);

  const isSqlite = dataset?.source_type === "sqlite";
  const isConfigured = !!dataset && dataset.columns.length > 0;

  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-300">{t("series.uploadIntro")}</p>
      <Button variant="secondary" onClick={() => fileRef.current?.click()} disabled={uploading}>
        {uploading ? t("common.loading") : t("series.chooseFile")}
      </Button>
      <input
        ref={fileRef}
        type="file"
        accept=".csv,.xls,.xlsx,.db,.sqlite,.sqlite3,text/csv,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/x-sqlite3,application/vnd.sqlite3"
        className="hidden"
        onChange={(e) => {
          const f = e.target.files?.[0];
          if (f) void onFile(f);
          e.target.value = "";
        }}
      />
      {uploadError && (
        <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {uploadError}
        </p>
      )}

      {dataset && isSqlite && (
        <SqliteConfigPanel
          dataset={dataset}
          configuring={configuring}
          configureError={configureError}
          onConfigure={onConfigureSqlite}
        />
      )}

      {dataset && (!isSqlite || isConfigured) && (
        <div className="rounded border border-emerald-900 bg-emerald-950/30 p-3 text-sm text-emerald-200">
          <p className="font-medium">{dataset.original_filename}</p>
          <p className="text-xs text-emerald-300">
            {dataset.row_count} {t("series.rows")} {" / "}
            {dataset.columns.length} {t("series.columns")}: {dataset.columns.join(", ")}
          </p>
          {isSqlite && dataset.sqlite_table && (
            <p className="mt-1 text-xs text-emerald-400">
              {t("series.sqliteSourceTable")}:{" "}
              <span className="font-mono">{dataset.sqlite_table}</span>
            </p>
          )}
          {isSqlite && dataset.sqlite_query && (
            <p className="mt-1 break-all text-xs text-emerald-400">
              {t("series.sqliteSourceQuery")}:{" "}
              <span className="font-mono">{dataset.sqlite_query}</span>
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function SqliteConfigPanel({
  dataset,
  configuring,
  configureError,
  onConfigure,
}: {
  dataset: DataSet;
  configuring: boolean;
  configureError: string | null;
  onConfigure: (input: { datasetId: number; table?: string; query?: string }) => Promise<void>;
}) {
  const { t } = useTranslation();
  // Surface non-empty tables first — an empty table can't be used for a series
  // (the renderer would have nothing to print). Tie-break alphabetically.
  const tables: SqliteTableInfo[] = useMemo(
    () =>
      [...(dataset.sqlite_tables ?? [])].sort(
        (a, b) => b.row_count - a.row_count || a.name.localeCompare(b.name),
      ),
    [dataset.sqlite_tables],
  );
  const [mode, setMode] = useState<"table" | "query">("table");
  const [selectedTable, setSelectedTable] = useState<string>(
    dataset.sqlite_table ?? tables[0]?.name ?? "",
  );
  const [customQuery, setCustomQuery] = useState<string>(
    dataset.sqlite_query ?? "SELECT * FROM your_table",
  );

  return (
    <div className="space-y-3 rounded border border-indigo-900 bg-indigo-950/30 p-3">
      <p className="text-sm text-indigo-200">{t("series.sqliteIntro")}</p>

      <div className="space-y-2">
        <label className="block text-xs font-medium uppercase tracking-wide text-indigo-300">
          {t("series.sqlitePickTable")}
        </label>
        {tables.length === 0 ? (
          <p className="text-xs text-indigo-400">{t("series.sqliteNoTables")}</p>
        ) : (
          <Select
            value={mode === "table" ? selectedTable : ""}
            onChange={(e) => {
              setMode("table");
              setSelectedTable(e.target.value);
            }}
          >
            {tables.map((tbl) => (
              <option key={tbl.name} value={tbl.name}>
                {tbl.name} ({tbl.columns.length} {t("series.columns")}, {tbl.row_count}{" "}
                {t("series.rows")})
              </option>
            ))}
          </Select>
        )}
      </div>

      <details className="rounded border border-indigo-900/60 bg-slate-900/40 p-2">
        <summary
          className="cursor-pointer text-xs font-medium text-indigo-300"
          onClick={() => setMode("query")}
        >
          {t("series.sqliteAdvanced")}
        </summary>
        <div className="mt-2 space-y-2">
          <textarea
            value={customQuery}
            onChange={(e) => {
              setMode("query");
              setCustomQuery(e.target.value);
            }}
            placeholder={t("series.sqliteQueryPlaceholder")}
            rows={5}
            className="w-full rounded border border-slate-700 bg-slate-950 px-2 py-1.5 font-mono text-xs text-slate-200 focus:border-indigo-500 focus:outline-none"
            spellCheck={false}
          />
          <p className="text-[10px] text-slate-500">{t("series.sqliteAdvancedHint")}</p>
        </div>
      </details>

      <div className="flex items-center gap-3">
        <Button
          onClick={() =>
            void onConfigure(
              mode === "table"
                ? { datasetId: dataset.id, table: selectedTable }
                : { datasetId: dataset.id, query: customQuery },
            )
          }
          disabled={
            configuring ||
            (mode === "table" && !selectedTable) ||
            (mode === "query" && !customQuery.trim())
          }
        >
          {configuring ? t("common.loading") : t("series.sqliteApply")}
        </Button>
        {dataset.columns.length > 0 && (
          <span className="text-xs text-emerald-400">
            ✓ {dataset.row_count} {t("series.rows")}, {dataset.columns.length} {t("series.columns")}
          </span>
        )}
      </div>

      {configureError && (
        <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {configureError}
        </p>
      )}
    </div>
  );
}

function MapStep({
  placeholders,
  columns,
  mapping,
  onChange,
}: {
  placeholders: string[];
  columns: string[];
  mapping: Record<string, string>;
  onChange: (m: Record<string, string>) => void;
}) {
  const { t } = useTranslation();
  if (placeholders.length === 0) {
    return <p className="text-sm text-slate-300">{t("series.noPlaceholders")}</p>;
  }
  return (
    <div className="space-y-3">
      <p className="text-sm text-slate-300">{t("series.mapIntro")}</p>
      <div className="space-y-2">
        {placeholders.map((ph) => (
          <div key={ph} className="grid grid-cols-2 items-center gap-3">
            <code className="rounded bg-indigo-900/40 px-2 py-1 font-mono text-sm text-indigo-200">{`{{${ph}}}`}</code>
            <div>
              <Select
                value={mapping[ph] ?? ""}
                onChange={(e) => onChange({ ...mapping, [ph]: e.target.value })}
              >
                <option value="">- {t("series.chooseColumn")} -</option>
                {columns.map((c) => (
                  <option key={c} value={c}>
                    {c}
                  </option>
                ))}
              </Select>
              {isPlainDateKey(ph) && !mapping[ph] && (
                <p className="mt-1 text-xs text-emerald-400">{t("series.dateAutoHint")}</p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function FilterStep({
  dataset,
  enabled,
  filter,
  onEnable,
  onChange,
  matchCount,
  onTest,
  testing,
}: {
  dataset: DataSet;
  enabled: boolean;
  filter: FilterSpec;
  onEnable: (b: boolean) => void;
  onChange: (f: FilterSpec) => void;
  matchCount: number | null;
  onTest: () => void;
  testing: boolean;
}) {
  const { t } = useTranslation();
  const needsValue = !["empty", "non_empty"].includes(filter.op);
  return (
    <div className="space-y-3">
      <label className="flex items-center gap-2 text-sm text-slate-200">
        <input
          type="checkbox"
          checked={enabled}
          onChange={(e) => onEnable(e.target.checked)}
          className="h-4 w-4 rounded border-slate-700 bg-slate-900"
        />
        {t("series.enableFilter")}
      </label>

      {enabled && (
        <div className="space-y-3 rounded border border-slate-800 bg-slate-900/30 p-3">
          <div className="grid grid-cols-3 gap-2">
            <Select
              value={filter.column}
              onChange={(e) => onChange({ ...filter, column: e.target.value })}
            >
              <option value="">- {t("series.column")} -</option>
              {dataset.columns.map((c) => (
                <option key={c} value={c}>
                  {c}
                </option>
              ))}
            </Select>
            <Select
              value={filter.op}
              onChange={(e) => onChange({ ...filter, op: e.target.value as FilterOp })}
            >
              {FILTER_OPS.map((op) => (
                <option key={op} value={op}>
                  {t(`series.op.${op}`)}
                </option>
              ))}
            </Select>
            {needsValue ? (
              <Input
                value={filter.value}
                onChange={(e) => onChange({ ...filter, value: e.target.value })}
                placeholder={t("series.value")}
              />
            ) : (
              <div />
            )}
          </div>
          <div className="flex items-center gap-3">
            <Button variant="secondary" onClick={onTest} disabled={testing || !filter.column}>
              {testing ? t("common.loading") : t("series.testFilter")}
            </Button>
            {matchCount !== null && (
              <span className="text-sm text-slate-300">
                {t("series.matchCount", {
                  count: matchCount,
                  total: dataset.row_count,
                })}
              </span>
            )}
          </div>
        </div>
      )}

      {!enabled && (
        <p className="text-sm text-slate-400">
          {t("series.filterSkipHint", { count: dataset.row_count })}
        </p>
      )}
    </div>
  );
}

function GenerateStep({
  dataset,
  mapping,
  filter,
  job,
  submitting,
  submitError,
  onSubmit,
}: {
  dataset: DataSet;
  mapping: Record<string, string>;
  filter: FilterSpec | null;
  job: {
    status: string;
    progress: number;
    total: number;
    error: string | null;
    warnings?: { object_id: string; row?: number; message: string }[];
  } | null;
  submitting: boolean;
  submitError: string | null;
  onSubmit: () => Promise<void>;
}) {
  const { t } = useTranslation();
  const mappingEntries = Object.entries(mapping);
  const status = job?.status;
  const progressPct = job && job.total > 0 ? Math.round((job.progress / job.total) * 100) : 0;

  return (
    <div className="space-y-4">
      <div className="space-y-1 text-sm text-slate-300">
        <p>
          <span className="text-slate-500">{t("series.summaryDataset")}:</span>{" "}
          <span className="font-mono">{dataset.original_filename}</span> {" / "} {dataset.row_count}{" "}
          {t("series.rows")}
        </p>
        {mappingEntries.length > 0 && (
          <p>
            <span className="text-slate-500">{t("series.summaryMapping")}:</span>{" "}
            {mappingEntries.map(([k, v]) => `${k}=${v}`).join(", ")}
          </p>
        )}
        {filter && (
          <p>
            <span className="text-slate-500">{t("series.summaryFilter")}:</span>{" "}
            <span className="font-mono">
              {filter.column} {filter.op} {filter.value}
            </span>
          </p>
        )}
      </div>

      {job === null && (
        <Button onClick={() => void onSubmit()} disabled={submitting} className="w-full">
          {submitting ? t("series.starting") : t("series.start")}
        </Button>
      )}

      {submitError && (
        <p className="rounded border border-rose-900 bg-rose-950/40 px-3 py-2 text-sm text-rose-300">
          {submitError}
        </p>
      )}

      {job && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm text-slate-300">
            <span>
              {status === "done"
                ? t("series.done")
                : status === "error"
                  ? t("series.failed")
                  : t("series.generating")}
            </span>
            <span className="font-mono text-xs">
              {job.progress} / {job.total} ({progressPct}%)
            </span>
          </div>
          <div className="h-2 overflow-hidden rounded-full bg-slate-800">
            <div
              className={[
                "h-full transition-all",
                status === "error" ? "bg-rose-500" : "bg-indigo-500",
              ].join(" ")}
              style={{ width: `${progressPct}%` }}
            />
          </div>
          {status === "error" && job.error && <p className="text-xs text-rose-400">{job.error}</p>}
          {status === "done" && (
            <p className="text-xs text-emerald-400">{t("series.downloadStarted")}</p>
          )}
          {status === "done" && job.warnings && job.warnings.length > 0 && (
            <div className="rounded-md border border-amber-900 bg-amber-950/40 p-3">
              <p className="text-sm font-medium text-amber-200">
                ⚠ {t("series.warningsTitle", { count: job.warnings.length })}
              </p>
              <ul className="mt-2 max-h-40 space-y-0.5 overflow-y-auto text-xs text-amber-300">
                {job.warnings.map((w, i) => (
                  <li key={`${w.row ?? "-"}-${w.object_id}-${i}`} className="font-mono">
                    {w.row !== undefined && (
                      <span className="text-amber-500">
                        {t("series.warningRow", { row: w.row })}{" "}
                      </span>
                    )}
                    <span className="text-amber-400">{w.object_id}:</span> {w.message}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
