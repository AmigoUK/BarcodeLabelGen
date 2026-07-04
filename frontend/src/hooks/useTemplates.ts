import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ApiError, api } from "../lib/api";
import { triggerDownload } from "../lib/download";
import { readCsrfCookie } from "../lib/csrf";
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
  folder_id: number | null;
  featured_asset_id: number | null;
  /** Present only in library listings — who shared this template. */
  owner_email: string | null;
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

/** Own templates; `folder` narrows to one folder id or "none" (unfiled). */
export function useTemplates(folder?: number | "none") {
  const param = folder !== undefined ? `?folder_id=${folder}` : "";
  return useQuery({
    queryKey: [...TEMPLATES_KEY, folder ?? "all"],
    queryFn: () =>
      api<{ templates: TemplateSummary[] }>(`/api/templates${param}`).then((r) => r.templates),
  });
}

/** Everything shared into the library (all owners, annotated with email). */
export function useLibraryTemplates() {
  return useQuery({
    queryKey: [...TEMPLATES_KEY, "library"],
    queryFn: () =>
      api<{ templates: TemplateSummary[] }>("/api/templates?scope=library").then(
        (r) => r.templates,
      ),
  });
}

export function useCloneTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: number) =>
      api<TemplateDetail>(`/api/templates/${id}/clone`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}

export type Starter = {
  slug: string;
  name: string;
  description: string | null;
  width_mm: number;
  height_mm: number;
};

export function useStarters() {
  return useQuery({
    queryKey: ["library", "starters"],
    queryFn: () => api<{ starters: Starter[] }>("/api/library/starters").then((r) => r.starters),
    staleTime: 5 * 60_000,
  });
}

export function useUseStarter() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (slug: string) =>
      api<TemplateDetail>(`/api/library/starters/${slug}/use`, { method: "POST" }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
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
  /** Override the format's preset dimensions (used for landscape
   * orientation and the user-defined Custom size). Both must be sent
   * together; the server falls back to the format's values for any
   * missing field. */
  width_mm?: number;
  height_mm?: number;
  /** Initial canvas — used when creating a template from captured ZPL. */
  canvas_data?: CanvasData;
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
    width_mm: number;
    height_mm: number;
    folder_id: number | null;
    featured_asset_id: number | null;
  }>;
};

/** Card thumbnail URL — access follows the template (works for shared). */
export const featuredImageUrl = (t: Pick<TemplateSummary, "id" | "updated_at">): string =>
  `/api/templates/${t.id}/featured-image?v=${encodeURIComponent(t.updated_at)}`;

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

// ---------------- Template export / import ----------------

export type AssetDupReport = {
  ref: string;
  sha256: string;
  matches_existing: boolean;
  existing_asset_id: number | null;
  existing_filename: string | null;
};

export type ObjectSummary = {
  id: string;
  type: string;
  label: string;
  has_dynamic: boolean;
};

export type ImportPreview = {
  template_name: string;
  width_mm: number;
  height_mm: number;
  object_summary: ObjectSummary[];
  asset_duplicates: AssetDupReport[];
  warnings: string[];
};

export type ImportOptions = {
  name?: string;
  width_mm?: number;
  height_mm?: number;
  skip_object_ids?: string[];
  asset_resolution?: Record<string, "reuse" | "new">;
};

/** Download a template as a `.blg-template.json` file. Uses fetch directly
 *  (rather than the JSON-y `api()` helper) so the response is treated as
 *  a binary blob rather than parsed. */
export async function exportTemplateToFile(templateId: number, fileName: string): Promise<void> {
  const csrf = readCsrfCookie();
  const response = await fetch(`/api/templates/${templateId}/export`, {
    credentials: "include",
    headers: csrf ? { "X-CSRF-Token": csrf } : undefined,
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as { error?: string; detail?: string };
    throw new ApiError(response.status, {
      error: body.error ?? "export_failed",
      detail: body.detail,
    });
  }
  const blob = await response.blob();
  triggerDownload(blob, fileName);
}

export function usePreviewImport() {
  return useMutation({
    mutationFn: (source: unknown) =>
      api<ImportPreview>("/api/templates/import/preview", {
        method: "POST",
        body: JSON.stringify(source),
      }),
  });
}

export function useImportTemplate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: { source: unknown; options: ImportOptions }) =>
      api<TemplateDetail>("/api/templates/import", {
        method: "POST",
        body: JSON.stringify(input),
      }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: TEMPLATES_KEY });
    },
  });
}
