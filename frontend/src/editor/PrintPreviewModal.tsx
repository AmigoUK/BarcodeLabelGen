/**
 * Print preview (F20): shows a freshly generated single-label PDF embedded in
 * the app, with Download / Close. The blob is generated once by the caller;
 * downloading here reuses it (one generation = one history entry).
 */

import { useEffect, useMemo } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { downloadPdfBlob, type PdfWarning } from "../hooks/useGeneratePdf";

type Props = {
  blob: Blob;
  warnings: PdfWarning[];
  filename: string;
  onClose: () => void;
};

export function PrintPreviewModal({ blob, warnings, filename, onClose }: Props) {
  const { t } = useTranslation();
  const url = useMemo(() => URL.createObjectURL(blob), [blob]);

  // Free the object URL when the preview closes (blob is otherwise held for
  // the page's lifetime).
  useEffect(() => () => URL.revokeObjectURL(url), [url]);

  return (
    <Modal
      open
      onClose={onClose}
      title={t("preview.title")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.close")}
          </Button>
          <Button onClick={() => downloadPdfBlob(blob, filename)}>{t("preview.download")}</Button>
        </>
      }
    >
      <div className="space-y-3">
        {warnings.length > 0 && (
          <div className="rounded-md border border-amber-900 bg-amber-950/40 px-3 py-2 text-xs text-amber-300">
            <p className="mb-1 font-medium">{t("preview.warnings", { count: warnings.length })}</p>
            <ul className="list-disc pl-4">
              {warnings.slice(0, 5).map((w, i) => (
                <li key={i}>{w.message}</li>
              ))}
            </ul>
          </div>
        )}
        <object
          data={url}
          type="application/pdf"
          className="h-[70vh] max-h-[70vh] w-full rounded border border-slate-700 bg-white"
          aria-label={t("preview.title")}
        >
          <p className="p-4 text-sm text-slate-300">
            {t("preview.embedFallback")}{" "}
            <a href={url} target="_blank" rel="noreferrer" className="text-indigo-400 underline">
              {t("preview.openInTab")}
            </a>
          </p>
        </object>
      </div>
    </Modal>
  );
}
