import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { readCsrfCookie } from "../lib/csrf";
import { triggerDownload } from "../lib/download";

export type GeneratedFile = {
  id: number;
  template_name: string;
  kind: "pdf" | "zpl";
  mode: "single" | "series";
  row_count: number | null;
  size_bytes: number;
  created_at: string;
};

const HISTORY_KEY = ["history"] as const;

export function useHistory() {
  return useQuery({
    queryKey: HISTORY_KEY,
    queryFn: () => api<{ files: GeneratedFile[] }>("/api/history").then((r) => r.files),
  });
}

export function useDeleteGeneratedFile() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/api/history/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: HISTORY_KEY });
    },
  });
}

/** Re-download a history file; server sets the filename via Content-Disposition
 *  but we pass a sensible one for the blob save too. */
export async function downloadHistoryFile(file: GeneratedFile): Promise<void> {
  const csrf = readCsrfCookie();
  const response = await fetch(`/api/history/${file.id}/download`, {
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
  });
  if (!response.ok) throw new Error(`download failed: ${response.status}`);
  const blob = await response.blob();
  const safe = file.template_name.replace(/[^A-Za-z0-9._-]+/g, "_") || "labels";
  triggerDownload(blob, `${safe}.${file.kind}`);
}
