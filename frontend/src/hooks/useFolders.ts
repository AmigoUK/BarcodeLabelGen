import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";

export type FolderSummary = {
  id: number;
  name: string;
  template_count: number | null;
  created_at: string;
};

const FOLDERS_KEY = ["folders"] as const;

export function useFolders() {
  return useQuery({
    queryKey: FOLDERS_KEY,
    queryFn: () => api<{ folders: FolderSummary[] }>("/api/folders").then((r) => r.folders),
  });
}

function invalidator(qc: ReturnType<typeof useQueryClient>) {
  return () => {
    void qc.invalidateQueries({ queryKey: FOLDERS_KEY });
    void qc.invalidateQueries({ queryKey: ["templates"] });
  };
}

export function useCreateFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (name: string) =>
      api<{ folder: FolderSummary }>("/api/folders", {
        method: "POST",
        body: JSON.stringify({ name }),
      }).then((r) => r.folder),
    onSuccess: invalidator(qc),
  });
}

export function useRenameFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, name }: { id: number; name: string }) =>
      api(`/api/folders/${id}`, { method: "PATCH", body: JSON.stringify({ name }) }),
    onSuccess: invalidator(qc),
  });
}

export function useDeleteFolder() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api(`/api/folders/${id}`, { method: "DELETE" }),
    onSuccess: invalidator(qc),
  });
}
