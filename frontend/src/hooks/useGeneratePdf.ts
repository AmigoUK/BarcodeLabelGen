import { useMutation } from "@tanstack/react-query";
import { readCsrfCookie } from "../lib/csrf";

/**
 * Triggers PDF generation on the backend and downloads the resulting
 * file directly. Returns the wall-clock duration of the request so the
 * caller can show a "Generated in X.Xs" toast if desired.
 */
export function useGeneratePdf() {
  return useMutation({
    mutationFn: async ({ templateId, filename }: { templateId: number; filename: string }) => {
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
      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
      return performance.now() - t0;
    },
  });
}
