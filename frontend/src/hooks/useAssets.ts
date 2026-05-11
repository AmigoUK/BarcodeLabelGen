import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../lib/api";
import { readCsrfCookie } from "../lib/csrf";

export type AssetMeta = {
  id: number;
  original_filename: string;
  mime_type: string;
  size_bytes: number;
  width_px: number;
  height_px: number;
  created_at: string;
};

const ASSETS_KEY = ["assets"] as const;

export function useAssets() {
  return useQuery({
    queryKey: ASSETS_KEY,
    queryFn: () => api<{ assets: AssetMeta[] }>("/api/assets/images").then((r) => r.assets),
  });
}

export function useUploadAsset() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData();
      form.append("file", file);
      const csrf = readCsrfCookie();
      const response = await fetch("/api/assets/images", {
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
      return (await response.json()) as AssetMeta;
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ASSETS_KEY });
    },
  });
}

/** Same-origin URL the browser hits to render an uploaded image. */
export const assetImageUrl = (id: number): string => `/api/assets/images/${id}`;
