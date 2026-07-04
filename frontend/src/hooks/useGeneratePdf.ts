import { useMutation } from "@tanstack/react-query";
import { readCsrfCookie } from "../lib/csrf";
import { triggerDownload } from "../lib/download";

export type PdfWarning = { object_id: string; message: string };

export type PdfGenerateResult = {
  blob: Blob;
  durationMs: number;
  warnings: PdfWarning[];
};

/**
 * Generate a single-label PDF on the backend and return the blob (plus the
 * optional `X-PDF-Warnings` soft-failure list and duration). The caller
 * decides what to do with the blob — download it (`downloadPdfBlob`) or show
 * it in a preview. Splitting fetch from download lets one code path back both
 * the "Download PDF" and "Preview" buttons.
 */
export function useGeneratePdf() {
  return useMutation({
    mutationFn: async ({ templateId }: { templateId: number }): Promise<PdfGenerateResult> => {
      const csrf = readCsrfCookie();
      const t0 = performance.now();
      const response = await fetch("/api/generate", {
        method: "POST",
        credentials: "include",
        headers: {
          "Content-Type": "application/json",
          ...(csrf ? { "X-CSRF-Token": csrf } : {}),
        },
        body: JSON.stringify({ template_id: templateId }),
      });
      if (!response.ok) {
        let detail = "PDF generation failed";
        try {
          const body = (await response.json()) as { error?: string; detail?: string };
          detail = body.detail ?? body.error ?? detail;
        } catch {
          // Body wasn't JSON — keep generic message
        }
        throw new Error(detail);
      }

      // Soft-failure list: header is set when the renderer hit conditions
      // worth surfacing (text overflow). Parse defensively — the header
      // is optional and a malformed value shouldn't blow up generation.
      let warnings: PdfWarning[] = [];
      const raw = response.headers.get("X-PDF-Warnings");
      if (raw) {
        try {
          const parsed = JSON.parse(raw) as unknown;
          if (Array.isArray(parsed)) warnings = parsed as PdfWarning[];
        } catch {
          // Ignore — corrupt header just means we show no chip.
        }
      }

      const blob = await response.blob();
      return { blob, durationMs: performance.now() - t0, warnings };
    },
  });
}

export function downloadPdfBlob(blob: Blob, filename: string): void {
  triggerDownload(blob, filename);
}
