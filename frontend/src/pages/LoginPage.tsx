import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate } from "react-router-dom";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { useLogin } from "../hooks/useAuth";
import { useMe } from "../hooks/useMe";
import { ApiError } from "../lib/api";

export function LoginPage() {
  const { t } = useTranslation();
  const { data: me, isLoading } = useMe();
  const login = useLogin();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  if (isLoading) return null;
  if (me) {
    return <Navigate to={me.must_change_password ? "/change-password" : "/"} replace />;
  }

  const errorMessage = (() => {
    if (!login.error) return null;
    if (login.error instanceof ApiError) {
      if (login.error.status === 401) return t("auth.errors.invalidCredentials");
      if (login.error.status === 403) return t("auth.errors.csrfFailed");
    }
    return t("auth.errors.generic");
  })();

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-950 p-6 text-slate-100">
      <div className="w-full max-w-md space-y-6">
        <div className="flex justify-end">
          <LanguageSwitcher />
        </div>
        <div className="space-y-2 text-center">
          <h1 className="text-3xl font-bold">{t("app.name")}</h1>
          <p className="text-slate-400">{t("auth.loginTitle")}</p>
        </div>
        <form
          className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            login.mutate({ email, password });
          }}
        >
          <Input
            label={t("auth.email")}
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <Input
            label={t("auth.password")}
            type="password"
            autoComplete="current-password"
            required
            value={password}
            onChange={(e) => setPassword(e.target.value)}
          />
          {errorMessage && (
            <div className="rounded-md border border-rose-900 bg-rose-950/50 px-3 py-2 text-sm text-rose-300">
              {errorMessage}
            </div>
          )}
          <Button type="submit" disabled={login.isPending} className="w-full">
            {login.isPending ? t("auth.loggingIn") : t("auth.loginButton")}
          </Button>
        </form>
      </div>
    </div>
  );
}
