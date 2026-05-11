import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import {
  useCreateTemplate,
  useDeleteTemplate,
  useLabelFormats,
  useTemplates,
} from "../hooks/useTemplates";

export function TemplatesPage() {
  const { t } = useTranslation();
  const templates = useTemplates();
  const del = useDeleteTemplate();
  const [showCreate, setShowCreate] = useState(false);
  const [query, setQuery] = useState("");

  const filtered = templates.data
    ? query.trim()
      ? templates.data.filter((tpl) => tpl.name.toLowerCase().includes(query.trim().toLowerCase()))
      : templates.data
    : [];

  return (
    <div className="space-y-6">
      <header className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold">{t("nav.templates")}</h1>
        <div className="flex items-center gap-2">
          {templates.data && templates.data.length > 0 && (
            <Input
              type="search"
              placeholder={t("templates.searchPlaceholder")}
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              className="w-64"
            />
          )}
          <Button onClick={() => setShowCreate(true)}>+ {t("templates.new")}</Button>
        </div>
      </header>

      {templates.isLoading && <p className="text-slate-400">{t("common.loading")}</p>}

      {templates.data && templates.data.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-10 text-center text-slate-400">
          {t("templates.empty")}
        </div>
      )}

      {templates.data && templates.data.length > 0 && filtered.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-700 bg-slate-900/40 p-10 text-center text-slate-400">
          {t("templates.noMatches", { query })}
        </div>
      )}

      {filtered.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {filtered.map((tpl) => (
            <a
              key={tpl.id}
              href={`/templates/${tpl.id}/edit`}
              className="group rounded-lg border border-slate-800 bg-slate-900/50 p-4 transition-colors hover:border-indigo-600"
            >
              <h3 className="mb-1 truncate font-semibold text-slate-100">{tpl.name}</h3>
              <p className="text-xs text-slate-500">
                {tpl.width_mm} × {tpl.height_mm} mm
              </p>
              {tpl.description && (
                <p className="mt-2 line-clamp-2 text-sm text-slate-400">{tpl.description}</p>
              )}
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>v{tpl.version}</span>
                <span>{new Date(tpl.updated_at).toLocaleDateString()}</span>
                <button
                  type="button"
                  onClick={(e) => {
                    e.preventDefault();
                    if (confirm(t("templates.confirmDelete", { name: tpl.name }))) {
                      del.mutate(tpl.id);
                    }
                  }}
                  className="rounded px-1.5 py-0.5 text-rose-400 opacity-0 hover:bg-rose-950/50 group-hover:opacity-100"
                  aria-label={t("common.delete")}
                >
                  ✕
                </button>
              </div>
            </a>
          ))}
        </div>
      )}

      {showCreate && <NewTemplateModal onClose={() => setShowCreate(false)} />}
    </div>
  );
}

function NewTemplateModal({ onClose }: { onClose: () => void }) {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const formats = useLabelFormats();
  const create = useCreateTemplate();

  const [name, setName] = useState("");
  const [formatId, setFormatId] = useState<number | "">("");

  const canSubmit = name.length > 0 && formatId !== "";

  return (
    <Modal
      open
      onClose={onClose}
      title={t("templates.new")}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            disabled={!canSubmit || create.isPending}
            onClick={() => {
              if (formatId === "") return;
              create.mutate(
                { name, format_id: Number(formatId) },
                {
                  onSuccess: (created) => {
                    onClose();
                    void navigate(`/templates/${created.id}/edit`);
                  },
                },
              );
            }}
          >
            {t("common.create")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Input
          label={t("templates.name")}
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <Select
          label={t("templates.format")}
          value={formatId}
          onChange={(e) => setFormatId(e.target.value === "" ? "" : Number(e.target.value))}
        >
          <option value="">— {t("templates.choose")} —</option>
          {formats.data?.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </Select>
        {create.error && (
          <p className="text-sm text-rose-400">
            {create.error instanceof Error ? create.error.message : String(create.error)}
          </p>
        )}
      </div>
    </Modal>
  );
}
