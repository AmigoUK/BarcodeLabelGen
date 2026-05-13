import { useTranslation } from "react-i18next";
import { Link } from "react-router-dom";
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

      <div className="grid gap-4 sm:grid-cols-2">
        <DashboardCard
          to="/templates"
          emoji="🏷️"
          title={t("dashboard.cards.templatesTitle")}
          body={t("dashboard.cards.templatesBody")}
          accent="indigo"
        />
        <DashboardCard
          to="/help"
          emoji="📖"
          title={t("dashboard.cards.helpTitle")}
          body={t("dashboard.cards.helpBody")}
          accent="slate"
        />
      </div>
    </div>
  );
}

function DashboardCard({
  to,
  emoji,
  title,
  body,
  accent,
}: {
  to: string;
  emoji: string;
  title: string;
  body: string;
  accent: "indigo" | "slate";
}) {
  // Two visual weights — the primary action is indigo, the secondary
  // (help) is muted slate so the user's eye lands on Templates first.
  const ring =
    accent === "indigo"
      ? "border-indigo-700 bg-indigo-950/30 hover:border-indigo-500 hover:bg-indigo-950/50"
      : "border-slate-700 bg-slate-900/40 hover:border-slate-500 hover:bg-slate-900/60";
  return (
    <Link to={to} className={`block rounded-lg border ${ring} p-5 transition-colors`}>
      <div className="mb-2 text-2xl">{emoji}</div>
      <h2 className="text-lg font-semibold text-slate-100">{title}</h2>
      <p className="mt-1 text-sm text-slate-400">{body}</p>
    </Link>
  );
}
