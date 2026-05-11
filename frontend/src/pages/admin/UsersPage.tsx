import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../../components/ui/Button";
import { Input } from "../../components/ui/Input";
import { Modal } from "../../components/ui/Modal";
import { Select } from "../../components/ui/Select";
import { useMe } from "../../hooks/useMe";
import { useCreateUser, useResetUserPassword, useUpdateUser, useUsers } from "../../hooks/useUsers";
import { ApiError } from "../../lib/api";
import type { Role, User } from "../../lib/types";

const ROLE_OPTIONS: Role[] = ["admin", "editor", "viewer"];

function generatePassword(length = 16): string {
  const alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!@#$%^&*";
  const out: string[] = [];
  const buf = new Uint32Array(length);
  crypto.getRandomValues(buf);
  for (const v of buf) out.push(alphabet[v % alphabet.length]);
  return out.join("");
}

function formatDate(iso: string | null, neverLabel: string): string {
  if (!iso) return neverLabel;
  return new Date(iso).toLocaleString();
}

export function UsersPage() {
  const { t } = useTranslation();
  const { data: me } = useMe();
  const { data: users, isLoading } = useUsers();
  const updateUser = useUpdateUser();

  const [showCreate, setShowCreate] = useState(false);
  const [resetTarget, setResetTarget] = useState<User | null>(null);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("admin.users.title")}</h1>
        <Button onClick={() => setShowCreate(true)}>+ {t("admin.users.create")}</Button>
      </header>

      {isLoading && <p className="text-slate-400">{t("common.loading")}</p>}

      {users && (
        <div className="overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-left text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">{t("auth.email")}</th>
                <th className="px-4 py-3">{t("admin.users.role")}</th>
                <th className="px-4 py-3">{t("admin.users.active")}</th>
                <th className="px-4 py-3">{t("admin.users.lastLogin")}</th>
                <th className="px-4 py-3">{t("admin.users.createdAt")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900/30">
              {users.map((u) => (
                <tr key={u.id}>
                  <td className="px-4 py-3 font-mono">
                    {u.email}
                    {u.must_change_password && (
                      <span
                        className="ml-2 rounded bg-amber-900/50 px-1.5 py-0.5 text-xs text-amber-300"
                        title="Must change password on next login"
                      >
                        ↻
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3">
                    <Select
                      value={u.role}
                      disabled={u.id === me?.id}
                      onChange={(e) =>
                        updateUser.mutate({
                          id: u.id,
                          patch: { role: e.target.value as Role },
                        })
                      }
                      className="!py-1 !text-xs"
                    >
                      {ROLE_OPTIONS.map((r) => (
                        <option key={r} value={r}>
                          {t(`admin.users.roles.${r}`)}
                        </option>
                      ))}
                    </Select>
                  </td>
                  <td className="px-4 py-3">
                    <label className="inline-flex cursor-pointer items-center">
                      <input
                        type="checkbox"
                        checked={u.is_active}
                        disabled={u.id === me?.id}
                        onChange={(e) =>
                          updateUser.mutate({
                            id: u.id,
                            patch: { is_active: e.target.checked },
                          })
                        }
                        className="h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600"
                      />
                    </label>
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {formatDate(u.last_login_at, t("admin.users.neverLoggedIn"))}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {formatDate(u.created_at, "—")}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button variant="ghost" onClick={() => setResetTarget(u)}>
                      {t("admin.users.resetPassword")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <CreateUserModal open={showCreate} onClose={() => setShowCreate(false)} />
      <ResetPasswordModal target={resetTarget} onClose={() => setResetTarget(null)} />
    </div>
  );
}

function CreateUserModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const create = useCreateUser();
  const [email, setEmail] = useState("");
  const [role, setRole] = useState<Role>("editor");
  const [language, setLanguage] = useState("pl");
  const [tempPassword, setTempPassword] = useState(() => generatePassword());
  const [createdPassword, setCreatedPassword] = useState<string | null>(null);

  const errorMessage = (() => {
    if (!create.error) return null;
    if (create.error instanceof ApiError) {
      if (create.error.code === "email_already_exists") {
        return t("admin.users.errors.emailExists");
      }
    }
    return t("auth.errors.generic");
  })();

  const reset = () => {
    setEmail("");
    setRole("editor");
    setLanguage("pl");
    setTempPassword(generatePassword());
    setCreatedPassword(null);
    create.reset();
  };

  if (createdPassword) {
    return (
      <Modal
        open={open}
        onClose={() => {
          reset();
          onClose();
        }}
        title={t("admin.users.tempPasswordCreatedTitle")}
        footer={
          <Button
            onClick={() => {
              reset();
              onClose();
            }}
          >
            {t("common.close")}
          </Button>
        }
      >
        <p className="mb-3 text-sm text-slate-300">{t("admin.users.tempPasswordCreatedBody")}</p>
        <code className="block break-all rounded-md bg-slate-950 p-3 font-mono text-sm text-emerald-300">
          {createdPassword}
        </code>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("admin.users.createTitle")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() =>
              create.mutate(
                { email, role, language, temporary_password: tempPassword },
                {
                  onSuccess: (data) => setCreatedPassword(data.temporary_password),
                },
              )
            }
            disabled={create.isPending || !email || tempPassword.length < 10}
          >
            {t("common.create")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label={t("auth.email")}
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          required
        />
        <Select
          label={t("admin.users.role")}
          value={role}
          onChange={(e) => setRole(e.target.value as Role)}
        >
          {ROLE_OPTIONS.map((r) => (
            <option key={r} value={r}>
              {t(`admin.users.roles.${r}`)}
            </option>
          ))}
        </Select>
        <Select
          label={t("common.language")}
          value={language}
          onChange={(e) => setLanguage(e.target.value)}
        >
          <option value="pl">Polski</option>
          <option value="en">English</option>
        </Select>
        <div>
          <Input
            label={t("admin.users.tempPassword")}
            value={tempPassword}
            onChange={(e) => setTempPassword(e.target.value)}
            hint={t("admin.users.tempPasswordHelp")}
          />
          <button
            type="button"
            onClick={() => setTempPassword(generatePassword())}
            className="mt-1 text-xs text-indigo-400 hover:text-indigo-300"
          >
            ↻ {t("admin.users.generatePassword")}
          </button>
        </div>
        {errorMessage && (
          <div className="rounded-md border border-rose-900 bg-rose-950/50 px-3 py-2 text-sm text-rose-300">
            {errorMessage}
          </div>
        )}
      </div>
    </Modal>
  );
}

function ResetPasswordModal({ target, onClose }: { target: User | null; onClose: () => void }) {
  const { t } = useTranslation();
  const reset = useResetUserPassword();
  const [password, setPassword] = useState(() => generatePassword());
  const [doneWith, setDoneWith] = useState<string | null>(null);

  if (!target) return null;

  const close = () => {
    setPassword(generatePassword());
    setDoneWith(null);
    reset.reset();
    onClose();
  };

  if (doneWith) {
    return (
      <Modal
        open
        onClose={close}
        title={t("admin.users.tempPasswordCreatedTitle")}
        footer={<Button onClick={close}>{t("common.close")}</Button>}
      >
        <p className="mb-3 text-sm text-slate-300">{t("admin.users.tempPasswordCreatedBody")}</p>
        <code className="block break-all rounded-md bg-slate-950 p-3 font-mono text-sm text-emerald-300">
          {doneWith}
        </code>
      </Modal>
    );
  }

  return (
    <Modal
      open
      onClose={close}
      title={`${t("admin.users.resetPasswordTitle")} — ${target.email}`}
      footer={
        <>
          <Button variant="secondary" onClick={close}>
            {t("common.cancel")}
          </Button>
          <Button
            variant="danger"
            onClick={() =>
              reset.mutate(
                { id: target.id, password },
                { onSuccess: (data) => setDoneWith(data.temporary_password) },
              )
            }
            disabled={reset.isPending || password.length < 10}
          >
            {t("admin.users.resetPassword")}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <Input
          label={t("admin.users.tempPassword")}
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          hint={t("admin.users.tempPasswordHelp")}
        />
        <button
          type="button"
          onClick={() => setPassword(generatePassword())}
          className="text-xs text-indigo-400 hover:text-indigo-300"
        >
          ↻ {t("admin.users.generatePassword")}
        </button>
      </div>
    </Modal>
  );
}
