import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { readCsrfCookie } from "../lib/csrf";

export type SqliteTableInfo = {
  name: string;
  columns: string[];
  row_count: number;
};

export type DataSet = {
  id: number;
  original_filename: string;
  /** Literal extension token; SQLite uploads keep their own ext ('db'/'sqlite'/'sqlite3'). */
  file_format: string;
  source_type: "csv" | "xlsx" | "sqlite";
  columns: string[];
  row_count: number;
  size_bytes: number;
  uploaded_at: string;
  sqlite_table: string | null;
  sqlite_query: string | null;
  /** Present only on the upload-response for SQLite files — drives the wizard's
   *  table-picker step. Not persisted, not returned by GET. */
  sqlite_tables?: SqliteTableInfo[];
};

export type SqliteConfigInput = {
  datasetId: number;
  table?: string;
  query?: string;
};

export type FilterOp = "eq" | "neq" | "contains" | "gt" | "lt" | "empty" | "non_empty";

export type FilterSpec = {
  column: string;
  op: FilterOp;
  value: string;
};

const DATASETS_KEY = ["datasets"] as const;

export function useDatasets() {
  return useQuery({
    queryKey: DATASETS_KEY,
    queryFn: () => api<{ datasets: DataSet[] }>("/api/datasets").then((r) => r.datasets),
  });
}

export function useUploadDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const csrf = readCsrfCookie();
      const response = await fetch("/api/datasets", {
        method: "POST",
        credentials: "include",
        headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
        body: form,
      });
      if (!response.ok) {
        const body = (await response.json().catch(() => ({}))) as {
          error?: string;
          detail?: string;
        };
        throw new Error(body.detail ?? body.error ?? "upload failed");
      }
      return (await response.json()) as DataSet;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DATASETS_KEY });
    },
  });
}

export function useDatasetPreview(datasetId: number | null, rows = 5) {
  return useQuery({
    queryKey: ["datasets", datasetId, "preview", rows] as const,
    queryFn: () =>
      api<{ rows: Record<string, string>[]; total: number }>(
        `/api/datasets/${datasetId}/preview?rows=${rows}`,
      ),
    enabled: datasetId !== null,
  });
}

export function useConfigureSqlite() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ datasetId, table, query }: SqliteConfigInput) =>
      api<DataSet>(`/api/datasets/${datasetId}/sqlite-config`, {
        method: "PATCH",
        body: JSON.stringify({ table, query }),
      }),
    onSuccess: (_, vars) => {
      void qc.invalidateQueries({ queryKey: DATASETS_KEY });
      void qc.invalidateQueries({ queryKey: ["datasets", vars.datasetId] });
    },
  });
}

export function useFilterDataset() {
  return useMutation({
    mutationFn: ({ datasetId, filter }: { datasetId: number; filter: FilterSpec }) =>
      api<{ match_count: number; preview: Record<string, string>[] }>(
        `/api/datasets/${datasetId}/filter`,
        {
          method: "POST",
          body: JSON.stringify(filter),
        },
      ),
  });
}

export function useDeleteDataset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/api/datasets/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: DATASETS_KEY });
    },
  });
}

// --- Jobs ---

export type JobStatus = "pending" | "running" | "done" | "error";

export type JobWarning = {
  object_id: string;
  row?: number;
  message: string;
};

export type JobState = {
  id: string;
  owner_id: number;
  template_id: number;
  status: JobStatus;
  progress: number;
  total: number;
  error: string | null;
  warnings?: JobWarning[];
};

export function useSubmitBatch() {
  return useMutation({
    mutationFn: (input: {
      template_id: number;
      dataset_id: number;
      mapping?: Record<string, string>;
      filter?: FilterSpec;
    }) =>
      api<{ job_id: string; total: number }>("/api/generate", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export function useJobStatus(jobId: string | null, pollMs = 1000) {
  return useQuery({
    queryKey: ["job", jobId] as const,
    queryFn: () => api<JobState>(`/api/jobs/${jobId}`),
    enabled: jobId !== null,
    refetchInterval: (q) => {
      const data = q.state.data as JobState | undefined;
      if (!data) return pollMs;
      return data.status === "done" || data.status === "error" ? false : pollMs;
    },
  });
}

/** Trigger a browser download of the finished job's PDF. */
export async function downloadJobPdf(jobId: string, filename: string): Promise<void> {
  const response = await fetch(`/api/jobs/${jobId}/download`, {
    credentials: "include",
  });
  if (!response.ok) throw new Error(`download failed: ${response.status}`);
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}
