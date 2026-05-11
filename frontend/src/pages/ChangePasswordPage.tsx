import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Navigate, useNavigate } from "react-router-dom";
import { LanguageSwitcher } from "../components/LanguageSwitcher";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { useChangePassword } from "../hooks/useAuth";
import { useMe } from "../hooks/useMe";
import { ApiError } from "../lib/api";

export function ChangePasswordPage() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { data: me, isLoading } = useMe();
  const change = useChangePassword();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");

  if (isLoading) return null;
  if (!me) return <Navigate to="/login" replace />;

  const localError = (() => {
    if (next && next.length < 10) return t("auth.errors.passwordTooShort");
    if (next && confirm && next !== confirm) return t("auth.errors.passwordsDontMatch");
    return null;
  })();

  const serverError = (() => {
    if (!change.error) return null;
    if (change.error instanceof ApiError) {
      if (change.error.code === "invalid_current_password") {
        return t("auth.errors.currentPasswordWrong");
      }
      if (change.error.code === "new_password_must_differ") {
        return t("auth.errors.newPasswordSameAsOld");
      }
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
          <h1 className="text-2xl font-bold">{t("auth.changePasswordTitle")}</h1>
          <p className="text-sm text-slate-400">{t("auth.changePasswordIntro")}</p>
        </div>
        <form
          className="space-y-4 rounded-lg border border-slate-800 bg-slate-900/50 p-6"
          onSubmit={(e) => {
            e.preventDefault();
            if (localError) return;
            change.mutate(
              { current_password: current, new_password: next },
              {
                onSuccess: () => navigate("/", { replace: true }),
              },
            );
          }}
        >
          <Input
            label={t("auth.currentPassword")}
            type="password"
            autoComplete="current-password"
            required
            value={current}
            onChange={(e) => setCurrent(e.target.value)}
          />
          <Input
            label={t("auth.newPassword")}
            type="password"
            autoComplete="new-password"
            required
            minLength={10}
            value={next}
            onChange={(e) => setNext(e.target.value)}
          />
          <Input
            label={t("auth.newPasswordConfirm")}
            type="password"
            autoComplete="new-password"
            required
            value={confirm}
            onChange={(e) => setConfirm(e.target.value)}
            error={localError ?? undefined}
          />
          {serverError && (
            <div className="rounded-md border border-rose-900 bg-rose-950/50 px-3 py-2 text-sm text-rose-300">
              {serverError}
            </div>
          )}
          <Button
            type="submit"
            disabled={change.isPending || !!localError || !current || !next || !confirm}
            className="w-full"
          >
            {t("auth.changePasswordButton")}
          </Button>
        </form>
      </div>
    </div>
  );
}
