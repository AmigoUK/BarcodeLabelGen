/**
 * Version history (F17): lists manual-save snapshots and restores one.
 * Restoring sets the template's canvas to that version and records the
 * restore itself as a new snapshot, so it stays undoable.
 */

import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Modal } from "../components/ui/Modal";
import { useRestoreVersion, useTemplateVersions } from "../hooks/useTemplateVersions";
import type { TemplateDetail } from "../hooks/useTemplates";

type Props = {
  templateId: number;
  onClose: () => void;
  onRestored: (restored: TemplateDetail) => void;
};

export function VersionHistoryModal({ templateId, onClose, onRestored }: Props) {
  const { t } = useTranslation();
  const versions = useTemplateVersions(templateId);
  const restore = useRestoreVersion(templateId);

  return (
    <Modal
      open
      onClose={onClose}
      title={t("history.title")}
      footer={<Button onClick={onClose}>{t("common.close")}</Button>}
    >
      <p className="mb-3 text-sm text-slate-400">{t("history.intro")}</p>

      {versions.isLoading && <p className="text-slate-400">{t("common.loading")}</p>}
      {versions.data && versions.data.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
          {t("history.empty")}
        </p>
      )}

      {versions.data && versions.data.length > 0 && (
        <div className="max-h-96 space-y-1 overflow-y-auto">
          {versions.data.map((v) => (
            <div
              key={v.version}
              className="flex items-center justify-between rounded border border-slate-800 bg-slate-900/40 px-3 py-2"
            >
              <div className="min-w-0">
                <p className="text-sm font-medium text-slate-100">
                  v{v.version}
                  {v.note && <span className="ml-2 text-xs text-amber-400">({v.note})</span>}
                </p>
                <p className="truncate text-xs text-slate-500">
                  {new Date(v.created_at).toLocaleString()}
                  {v.created_by_email ? ` · ${v.created_by_email}` : ""}
                </p>
              </div>
              <Button
                variant="secondary"
                disabled={restore.isPending}
                onClick={() => {
                  if (window.confirm(t("history.confirmRestore", { version: v.version }))) {
                    restore.mutate(v.version, {
                      onSuccess: (restored) => {
                        onRestored(restored);
                        onClose();
                      },
                    });
                  }
                }}
              >
                {t("history.restore")}
              </Button>
            </div>
          ))}
        </div>
      )}
      {restore.error && (
        <p className="mt-2 text-sm text-rose-400">{t("auth.errors.generic")}</p>
      )}
    </Modal>
  );
}
