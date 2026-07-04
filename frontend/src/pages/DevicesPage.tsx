/**
 * Settings → Devices: local connector agents (blg-connector). Creating a
 * device mints its Bearer token, shown exactly once — afterwards only the
 * hash lives server-side.
 */

import { useState } from "react";
import { useTranslation } from "react-i18next";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { useCreateDevice, useDeleteDevice, useDevices } from "../hooks/useDevices";
import { ApiError } from "../lib/api";
import type { Device } from "../lib/types";

const ONLINE_WINDOW_MS = 60_000;

function isOnline(device: Device): boolean {
  if (!device.last_seen_at) return false;
  return Date.now() - new Date(device.last_seen_at).getTime() < ONLINE_WINDOW_MS;
}

function formatDate(iso: string | null, neverLabel: string): string {
  if (!iso) return neverLabel;
  return new Date(iso).toLocaleString();
}

export function DevicesPage() {
  const { t } = useTranslation();
  const { data: devices, isLoading } = useDevices();
  const deleteDevice = useDeleteDevice();
  const [showCreate, setShowCreate] = useState(false);

  return (
    <div className="space-y-6">
      <header className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t("devices.title")}</h1>
        <Button onClick={() => setShowCreate(true)}>+ {t("devices.create")}</Button>
      </header>

      <p className="max-w-3xl text-sm text-slate-400">{t("devices.intro")}</p>

      {isLoading && <p className="text-slate-400">{t("common.loading")}</p>}

      {devices && devices.length === 0 && (
        <p className="rounded-lg border border-dashed border-slate-700 p-6 text-center text-sm text-slate-400">
          {t("devices.empty")}
        </p>
      )}

      {devices && devices.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-slate-800">
          <table className="w-full text-sm">
            <thead className="bg-slate-900 text-left text-xs uppercase tracking-wider text-slate-400">
              <tr>
                <th className="px-4 py-3">{t("devices.name")}</th>
                <th className="px-4 py-3">{t("devices.status")}</th>
                <th className="px-4 py-3">{t("devices.printers")}</th>
                <th className="px-4 py-3">{t("devices.lastSeen")}</th>
                <th className="px-4 py-3">{t("devices.agentVersion")}</th>
                <th className="px-4 py-3"></th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800 bg-slate-900/30">
              {devices.map((d) => (
                <tr key={d.id}>
                  <td className="px-4 py-3 font-medium">{d.name}</td>
                  <td className="px-4 py-3">
                    {isOnline(d) ? (
                      <span className="inline-flex items-center gap-1.5 text-emerald-400">
                        <span className="h-2 w-2 rounded-full bg-emerald-400" />
                        {t("devices.online")}
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1.5 text-slate-500">
                        <span className="h-2 w-2 rounded-full bg-slate-600" />
                        {t("devices.offline")}
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-300">
                    {d.printers.length === 0
                      ? "—"
                      : d.printers.map((p) => p.name).join(", ")}
                  </td>
                  <td className="px-4 py-3 text-xs text-slate-400">
                    {formatDate(d.last_seen_at, t("devices.neverSeen"))}
                  </td>
                  <td className="px-4 py-3 font-mono text-xs text-slate-400">
                    {d.agent_version ?? "—"}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Button
                      variant="ghost"
                      onClick={() => {
                        if (window.confirm(t("devices.confirmDelete", { name: d.name }))) {
                          deleteDevice.mutate(d.id);
                        }
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

      <CreateDeviceModal open={showCreate} onClose={() => setShowCreate(false)} />
    </div>
  );
}

function CreateDeviceModal({ open, onClose }: { open: boolean; onClose: () => void }) {
  const { t } = useTranslation();
  const create = useCreateDevice();
  const [name, setName] = useState("");
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);

  const errorMessage = (() => {
    if (!create.error) return null;
    if (create.error instanceof ApiError && create.error.code === "device_name_taken") {
      return t("devices.errors.nameTaken");
    }
    return t("auth.errors.generic");
  })();

  const reset = () => {
    setName("");
    setCreatedToken(null);
    setCopied(false);
    create.reset();
  };

  if (createdToken) {
    return (
      <Modal
        open={open}
        onClose={() => {
          reset();
          onClose();
        }}
        title={t("devices.tokenCreatedTitle")}
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
        <p className="mb-3 text-sm text-slate-300">{t("devices.tokenCreatedBody")}</p>
        <code className="block break-all rounded-md bg-slate-950 p-3 font-mono text-sm text-emerald-300">
          {createdToken}
        </code>
        <Button
          variant="secondary"
          className="mt-3"
          onClick={() => {
            void navigator.clipboard.writeText(createdToken).then(() => setCopied(true));
          }}
        >
          {copied ? t("devices.copied") : t("devices.copyToken")}
        </Button>
      </Modal>
    );
  }

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={t("devices.createTitle")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={() =>
              create.mutate(name.trim(), {
                onSuccess: (data) => setCreatedToken(data.token),
              })
            }
            disabled={create.isPending || !name.trim()}
          >
            {t("common.create")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label={t("devices.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          placeholder={t("devices.namePlaceholder")}
          required
        />
        <p className="text-xs text-slate-500">{t("devices.createHint")}</p>
        {errorMessage && (
          <div className="rounded-md border border-rose-900 bg-rose-950/50 px-3 py-2 text-sm text-rose-300">
            {errorMessage}
          </div>
        )}
      </div>
    </Modal>
  );
}
