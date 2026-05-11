import { useTranslation } from "react-i18next";
import { useMe } from "../hooks/useMe";

export function DashboardPage() {
  const { t } = useTranslation();
  const { data: me } = useMe();

  return (
    <div className="space-y-6">
      <header className="space-y-1">
        <h1 className="text-3xl font-bold">{t("dashboard.title")}</h1>
        <p className="text-slate-400">{t("dashboard.welcome", { email: me?.email ?? "" })}</p>
      </header>
      <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-8 text-center text-slate-400">
        {t("dashboard.comingSoon")}
      </div>
    </div>
  );
}
