import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import type { CanvasData } from "../editor/types";

export type LabelFormat = {
  id: number;
  name: string;
  width_mm: number;
  height_mm: number;
  kind: "a_paper" | "zebra" | "custom";
  is_system: boolean;
};

export type TemplateSummary = {
  id: number;
  name: string;
  description: string | null;
  owner_id: number;
  format_id: number;
  width_mm: number;
  height_mm: number;
  is_shared: boolean;
  version: number;
  created_at: string;
  updated_at: string;
};

export type TemplateDetail = TemplateSummary & {
  canvas_data: CanvasData;
};

const FORMATS_KEY = ["label-formats"] as const;
const TEMPLATES_KEY = ["templates"] as const;

export function useLabelFormats() {
  return useQuery({
    queryKey: FORMATS_KEY,
    queryFn: () => api<{ formats: LabelFormat[] }>("/api/label-formats").then((r) => r.formats),
    staleTime: 5 * 60_000,
  });
}

export function useTemplates() {
  return useQuery({
    queryKey: TEMPLATES_KEY,
    queryFn: () => api<{ templates: TemplateSummary[] }>("/api/templates").then((r) => r.templates),
  });
}

export function useTemplate(id: number | null) {
  return useQuery({
    queryKey: ["templates", id] as const,
    queryFn: () => api<TemplateDetail>(`/api/templates/${id}`),
    enabled: id !== null,
  });
}

type CreateTemplateInput = {
  name: string;
  format_id: number;
  description?: string | null;
};

export function useCreateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: CreateTemplateInput) =>
      api<TemplateDetail>("/api/templates", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

type UpdateTemplateInput = {
  id: number;
  patch: Partial<{
    name: string;
    description: string | null;
    canvas_data: CanvasData;
    is_shared: boolean;
  }>;
};

export function useUpdateTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, patch }: UpdateTemplateInput) =>
      api<TemplateDetail>(`/api/templates/${id}`, {
        method: "PUT",
        body: JSON.stringify(patch),
      }),
    onSuccess: (data) => {
      qc.setQueryData(["templates", data.id], data);
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

export function useDeleteTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) => api<void>(`/api/templates/${id}`, { method: "DELETE" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}
