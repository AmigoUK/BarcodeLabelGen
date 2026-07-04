import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { TemplateDetail } from "./useTemplates";

export type VersionSummary = {
  version: number;
  note: string | null;
  created_at: string;
  created_by_email: string | null;
};

export function useTemplateVersions(templateId: number) {
  return useQuery({
    queryKey: ["template-versions", templateId],
    queryFn: () =>
      api<{ versions: VersionSummary[] }>(`/api/templates/${templateId}/versions`).then(
        (r) => r.versions,
      ),
  });
}

export function useRestoreVersion(templateId: number) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (version: number) =>
      api<TemplateDetail>(`/api/templates/${templateId}/versions/${version}/restore`, {
        method: "POST",
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["template-versions", templateId] });
      void qc.invalidateQueries({ queryKey: ["templates", templateId] });
    },
  });
}
