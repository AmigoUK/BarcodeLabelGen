import type { ReactNode } from "react";
import { useTranslation } from "react-i18next";
import { Link, NavLink } from "react-router-dom";
import { AppFooter } from "../components/AppFooter";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { Button } from "../components/ui/Button";
import { useLogout } from "../hooks/useAuth";
import { useMe } from "../hooks/useMe";

type Props = { children: ReactNode };

export function AppLayout({ children }: Props) {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const logout = useLogout();

  const navItem = (to: string, label: string) => (
    <NavLink
      to={to}
      end
      className={({ isActive }) =>
        [
          "rounded-md px-3 py-2 text-sm font-medium transition-colors",
          isActive
            ? "bg-indigo-600 text-white"
            : "text-slate-300 hover:bg-slate-800 hover:text-white",
        ].join(" ")
      }
    >
      {label}
    </NavLink>
  );

  return (
    <div className="flex min-h-screen bg-slate-950 text-slate-100">
      <aside className="hidden w-64 border-r border-slate-800 bg-slate-900/40 p-4 sm:block">
        <Link to="/" className="mb-6 block">
          <h1 className="text-lg font-bold tracking-tight">{t("app.name")}</h1>
          <p className="text-xs text-slate-500">{t("app.tagline")}</p>
        </Link>
        <nav className="flex flex-col gap-1">
          {navItem("/", t("nav.dashboard"))}
          {navItem("/templates", t("nav.templates"))}
          {navItem("/help", t("nav.help"))}
          {me?.role === "admin" && (
            <>
              <div className="mt-4 px-3 text-xs uppercase tracking-wider text-slate-500">
                {t("nav.admin")}
              </div>
              {navItem("/admin/users", t("nav.users"))}
            </>
          )}
        </nav>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center justify-between border-b border-slate-800 px-6 py-3">
          <div className="text-sm text-slate-400">
            {me && <span className="font-mono">{me.email}</span>}
          </div>
          <div className="flex items-center gap-3">
            <LanguageSwitcher />
            <Button variant="ghost" onClick={() => logout.mutate()}>
              {t("auth.logout")}
            </Button>
          </div>
        </header>

        <main className="flex-1 overflow-y-auto p-6">{children}</main>
        <AppFooter />
      </div>
    </div>
  );
}
