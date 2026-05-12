import { useMutation } from "@tanstack/react-query";
import { readCsrfCookie } from "../lib/csrf";

export type PdfWarning = { object_id: string; message: string };

export type PdfGenerateResult = {
  durationMs: number;
  warnings: PdfWarning[];
};

/**
 * Triggers PDF generation on the backend and downloads the resulting
 * file directly. Reads the optional `X-PDF-Warnings` response header
 * (JSON-encoded list of soft-failure entries — currently text-block
 * overflow at minimum font size) and returns it alongside the duration
 * so the caller can surface a UI chip.
 */
export function useGeneratePdf() {
  return useMutation({
    mutationFn: async ({
      templateId,
      filename,
    }: {
      templateId: number;
      filename: string;
    }): Promise<PdfGenerateResult> => {
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
      // is optional and a malformed value shouldn't blow up the download.
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
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);

      return { durationMs: performance.now() - t0, warnings };
    },
  });
}
