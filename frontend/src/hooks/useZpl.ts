import { useMutation } from "@tanstack/react-query";
import type { CanvasData } from "../editor/types";
import { api } from "../lib/api";
import { readCsrfCookie } from "../lib/csrf";

export type ZplWarning = { object_id: string; row?: number; message: string };

export type ZplParseResult = {
  canvas_data: CanvasData;
  warnings: ZplWarning[];
  /** The DPI actually used — echoes the request, or the detected value when
   *  `dpi: "auto"` was sent. */
  detected_dpi?: number;
};

export type ParseZplInput = {
  zpl: string;
  /** A concrete DPI or "auto" to detect it from ^PW/^LL vs the label size. */
  dpi: number | "auto";
  target_width_mm?: number;
  target_height_mm?: number;
};

/** Parse pasted ZPL into an editable canvas tree. */
export function useParseZpl() {
  return useMutation({
    mutationFn: (input: ParseZplInput) =>
      api<ZplParseResult>("/api/zpl/parse", {
        method: "POST",
        body: JSON.stringify(input),
      }),
  });
}

export type ZplGenerateResult = {
  zpl: string;
  warnings: ZplWarning[];
};

/**
 * Generate ZPL from a canvas (template / live-preview mode). Sends the
 * current editor canvas so the preview reflects unsaved edits, and reads
 * the optional `X-ZPL-Warnings` header (e.g. an image object that can't be
 * emitted natively).
 */
export function useGenerateZpl() {
  return useMutation({
    mutationFn: async (input: {
      canvas_data: CanvasData;
      dpi: number;
    }): Promise<ZplGenerateResult> => {
      const csrf = readCsrfCookie();
      const response = await fetch("/api/zpl/generate", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: JSON.stringify({ ...input, mode: "template" }),
      });
      if (!response.ok) {
        let detail = "ZPL generation failed";
        try {
          const body = (await response.json()) as { error?: string; detail?: string };
          detail = body.detail ?? body.error ?? detail;
        } catch {
          // non-JSON body — keep generic message
        }
        throw new Error(detail);
      }
      let warnings: ZplWarning[] = [];
      const raw = response.headers.get("X-ZPL-Warnings");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (Array.isArray(parsed)) warnings = parsed as ZplWarning[];
        } catch {
          // corrupt header → no warnings chip
        }
      }
      const zpl = await response.text();
      return { zpl, warnings };
    },
  });
}

/** Submit a batch ZPL job (dataset {{column}} substitution, one label per
 *  row). Mirrors useSubmitBatch but targets the ZPL endpoint; poll with
 *  useJobStatus and download with downloadJobPdf (generic filename). */
export function useSubmitZplBatch() {
  return useMutation({
    mutationFn: (input: {
      template_id: number;
      dataset_id: number;
      dpi: number;
      mapping?: Record<string, string>;
    }) =>
      api<{ job_id: string; total: number }>("/api/zpl/generate", {
        method: "POST",
        body: JSON.stringify({ ...input, mode: "batch" }),
      }),
  });
}
