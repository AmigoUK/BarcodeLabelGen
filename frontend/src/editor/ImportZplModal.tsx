import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import { type ZplWarning, useParseZpl } from "../hooks/useZpl";
import type { CanvasData } from "./types";

type Props = {
  open: boolean;
  onClose: () => void;
  /** Called with the parsed canvas when the user confirms the import.
   *  Replaces the editor canvas — the caller marks it dirty. */
  onImported: (canvas: CanvasData) => void;
};

export function ImportZplModal({ open, onClose, onImported }: Props) {
  const { t } = useTranslation();
  const parse = useParseZpl();
  const [zpl, setZpl] = useState("");
  const [dpi, setDpi] = useState(203);
  const [warnings, setWarnings] = useState<ZplWarning[]>([]);

  const reset = () => {
    setZpl("");
    setWarnings([]);
    parse.reset();
  };

  const handleClose = () => {
    reset();
    onClose();
  };

  const handleImport = () => {
    parse.mutate(
      { zpl, dpi },
      {
        onSuccess: (result) => {
          setWarnings(result.warnings);
          onImported(result.canvas_data);
          reset();
          onClose();
        },
      },
    );
  };

  const error = parse.error
    ? parse.error instanceof Error
      ? parse.error.message
      : String(parse.error)
    : null;

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title={t("zpl.importTitle")}
      footer={
        <>
          <Button variant="ghost" onClick={handleClose}>
            {t("common.cancel")}
          </Button>
          <Button onClick={handleImport} disabled={parse.isPending || zpl.trim().length === 0}>
            {parse.isPending ? t("common.loading") : t("zpl.importAction")}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-slate-400">{t("zpl.importHelp")}</p>
        <textarea
          value={zpl}
          onChange={(e) => setZpl(e.target.value)}
          spellCheck={false}
          placeholder="^XA&#10;^FO50,50^A@N,28,28,E:ARI001.TTF^FD{NAZWA}^FS&#10;^XZ"
          className="h-56 w-full resize-y rounded-md border border-slate-700 bg-slate-950 px-3 py-2 font-mono text-xs text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
        <div className="flex items-center gap-3">
          <div className="w-40">
            <Select
              label={t("zpl.dpi")}
              value={dpi}
              onChange={(e) => setDpi(Number(e.target.value))}
            >
              <option value={203}>203 dpi (8 dpmm)</option>
              <option value={300}>300 dpi (12 dpmm)</option>
            </Select>
          </div>
          <p className="mt-5 text-xs text-amber-300">{t("zpl.importReplaceWarning")}</p>
        </div>
        {error && <p className="text-sm text-rose-400">{error}</p>}
        {warnings.length > 0 && (
          <ul className="max-h-24 overflow-auto rounded bg-amber-900/30 p-2 text-xs text-amber-200">
            {warnings.map((w, i) => (
              <li key={i}>• {w.message}</li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  );
}
