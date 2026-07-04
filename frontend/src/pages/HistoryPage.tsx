/**
 * History (F18): generated PDFs and batch ZPL, re-downloadable for 30 days.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import {
  type GeneratedFile,
  downloadHistoryFile,
  useDeleteGeneratedFile,
  useHistory,
} from "../hooks/useGeneratedFiles";

function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} kB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export function HistoryPage() {
  const { t } = useTranslation();
  const { data: files, isLoading } = useHistory();
  const del = useDeleteGeneratedFile();
  const [busyId, setBusyId] = useState<number | null>(null);

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold">{t("nav.history")}</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">{t("historyPage.intro")}</p>
      </header>

      {isLoading && <p className="text-slate-400">{t("common.loading")}</p>}

      {files && files.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
          {t("historyPage.empty")}
        </p>
      )}

      {files && files.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-left text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">{t("historyPage.template")}</th>
                <th className="px-4 py-3">{t("historyPage.type")}</th>
                <th className="px-4 py-3">{t("historyPage.labels")}</th>
                <th className="px-4 py-3">{t("historyPage.size")}</th>
                <th className="px-4 py-3">{t("historyPage.generatedAt")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900/30">
              {files.map((f: GeneratedFile) => (
                <tr key={f.id}>
                  <td className="px-4 py-3 font-medium text-slate-100">{f.template_name}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {f.kind.toUpperCase()} ·{" "}
                    {f.mode === "series" ? t("historyPage.series") : t("historyPage.single")}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">{f.row_count ?? "1"}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">{formatBytes(f.size_bytes)}</td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {new Date(f.created_at).toLocaleString()}
                  </td>
                  <td className="space-x-2 px-4 py-3 text-right">
                    <Button
                      variant="secondary"
                      disabled={busyId === f.id}
                      onClick={() => {
                        setBusyId(f.id);
                        void downloadHistoryFile(f).finally(() => setBusyId(null));
                      }}
                    >
                      {t("historyPage.download")}
                    </Button>
                    <Button
                      variant="ghost"
                      onClick={() => {
                        if (window.confirm(t("historyPage.confirmDelete"))) del.mutate(f.id);
                      }}
                    >
                      {t("common.delete")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
