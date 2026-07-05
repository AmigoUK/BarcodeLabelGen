import { useMutation } from "@tanstack/react-query";
import type { CanvasData } from "../editor/types";
import { readCsrfCookie } from "../lib/csrf";

export type TsplWarning = { object_id: string; row?: number; message: string };

export type TsplGenerateResult = {
  tspl: string;
  warnings: TsplWarning[];
};

/**
 * Generate TSPL from a canvas (single-label mode). Sends the live editor
 * canvas and reads the optional `X-TSPL-Warnings` header (e.g. an image
 * object that can't be emitted, or an approximated font).
 */
export function useGenerateTspl() {
  return useMutation({
    mutationFn: async (input: {
      canvas_data: CanvasData;
      dpi: number;
    }): Promise<TsplGenerateResult> => {
      const csrf = readCsrfCookie();
      const response = await fetch("/api/tspl/generate", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: JSON.stringify(input),
      });
      if (!response.ok) {
        let detail = "TSPL generation failed";
        try {
          const body = (await response.json()) as { error?: string; detail?: string };
          detail = body.detail ?? body.error ?? detail;
        } catch {
          // non-JSON body — keep generic message
        }
        throw new Error(detail);
      }
      let warnings: TsplWarning[] = [];
      const raw = response.headers.get("X-TSPL-Warnings");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (Array.isArray(parsed)) warnings = parsed as TsplWarning[];
        } catch {
          // corrupt header — no warnings chip
        }
      }
      const tspl = await response.text();
      return { tspl, warnings };
    },
  });
}
