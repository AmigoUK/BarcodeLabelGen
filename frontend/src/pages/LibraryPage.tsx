/**
 * Library (F31): bundled starter templates + everything users shared.
 * "Użyj" always clones into the caller's own templates and opens the editor.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { useMe } from "../hooks/useMe";
import {
  featuredImageUrl,
  useCloneTemplate,
  useLibraryTemplates,
  useStarters,
  useUseStarter,
} from "../hooks/useTemplates";

export function LibraryPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: me } = useMe();
  const starters = useStarters();
  const shared = useLibraryTemplates();
  const useStarter = useUseStarter();
  const cloneTemplate = useCloneTemplate();
  const [busy, setBusy] = useState<string | null>(null);

  const openCreated = (id: number) => void navigate(`/templates/${id}/edit`);

  return (
    <div className="space-y-8">
      <header>
        <h1 className="text-2xl font-bold">{t("library.title")}</h1>
        <p className="mt-1 max-w-3xl text-sm text-slate-400">{t("library.intro")}</p>
      </header>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">{t("library.starters")}</h2>
        {starters.isLoading && <p className="text-slate-400">{t("common.loading")}</p>}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {starters.data?.map((s) => (
            <div
              key={s.slug}
              className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/50 p-4"
            >
              <h3 className="font-semibold text-slate-100">{s.name}</h3>
              <p className="text-xs text-slate-500">
                {s.width_mm} × {s.height_mm} mm
              </p>
              {s.description && (
                <p className="mt-2 flex-1 text-sm text-slate-400">{s.description}</p>
              )}
              <div className="mt-3">
                <Button
                  disabled={busy !== null}
                  onClick={() => {
                    setBusy(s.slug);
                    useStarter.mutate(s.slug, {
                      onSuccess: (tpl) => openCreated(tpl.id),
                      onSettled: () => setBusy(null),
                    });
                  }}
                >
                  {busy === s.slug ? t("common.loading") : t("library.use")}
                </Button>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold">{t("library.fromUsers")}</h2>
        {shared.isLoading && <p className="text-slate-400">{t("common.loading")}</p>}
        {shared.data && shared.data.length === 0 && (
          <p className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
            {t("library.emptyShared")}
          </p>
        )}
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {shared.data?.map((tpl) => {
            const own = tpl.owner_id === me?.id;
            return (
              <div
                key={tpl.id}
                className="flex flex-col rounded-lg border border-slate-800 bg-slate-900/50 p-4"
              >
                {tpl.featured_asset_id !== null && (
                  <img
                    src={featuredImageUrl(tpl)}
                    alt=""
                    loading="lazy"
                    className="mb-3 h-24 w-full rounded object-cover"
                  />
                )}
                <h3 className="font-semibold text-slate-100">{tpl.name}</h3>
                <p className="text-xs text-slate-500">
                  {tpl.width_mm} × {tpl.height_mm} mm · {tpl.owner_email}
                </p>
                {tpl.description && (
                  <p className="mt-2 flex-1 text-sm text-slate-400">{tpl.description}</p>
                )}
                <div className="mt-3">
                  {own ? (
                    <span className="text-xs text-slate-500">{t("library.yourTemplate")}</span>
                  ) : (
                    <Button
                      disabled={busy !== null}
                      onClick={() => {
                        setBusy(`tpl-${tpl.id}`);
                        cloneTemplate.mutate(tpl.id, {
                          onSuccess: (created) => openCreated(created.id),
                          onSettled: () => setBusy(null),
                        });
                      }}
                    >
                      {busy === `tpl-${tpl.id}` ? t("common.loading") : t("library.use")}
                    </Button>
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
