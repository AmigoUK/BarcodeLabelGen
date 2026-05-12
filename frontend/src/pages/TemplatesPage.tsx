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
  const [orientation, setOrientation] = useState<"portrait" | "landscape">("portrait");
  const [customW, setCustomW] = useState<number>(80);
  const [customH, setCustomH] = useState<number>(60);

  const fmt = formats.data?.find((f) => f.id === formatId) ?? null;
  const isCustom = fmt?.kind === "custom";
  const isSquare = !!fmt && !isCustom && fmt.width_mm === fmt.height_mm;
  const showOrientation = !!fmt && !isCustom && !isSquare;

  // Resolve the dimensions the user is about to commit to — same math
  // we'll send to the backend below. Used for the live "Wybrano: …"
  // hint and for validation.
  const resolved = (() => {
    if (!fmt) return null;
    if (isCustom) return { w: customW, h: customH };
    if (orientation === "landscape") return { w: fmt.height_mm, h: fmt.width_mm };
    return { w: fmt.width_mm, h: fmt.height_mm };
  })();

  const customInRange =
    !isCustom || (customW >= 10 && customW <= 1000 && customH >= 10 && customH <= 1000);
  const canSubmit = name.length > 0 && formatId !== "" && customInRange;

  // Group formats so the custom row sits below a divider rather than
  // mixed in with the system presets.
  const presetFormats = formats.data?.filter((f) => f.kind !== "custom") ?? [];
  const customFormats = formats.data?.filter((f) => f.kind === "custom") ?? [];

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
              if (formatId === "" || !resolved) return;
              create.mutate(
                {
                  name,
                  format_id: Number(formatId),
                  width_mm: resolved.w,
                  height_mm: resolved.h,
                },
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
          {presetFormats.length > 0 && (
            <optgroup label={t("templates.presetGroup")}>
              {presetFormats.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </optgroup>
          )}
          {customFormats.length > 0 && (
            <optgroup label={t("templates.customGroup")}>
              {customFormats.map((f) => (
                <option key={f.id} value={f.id}>
                  {t("templates.customSize")}
                </option>
              ))}
            </optgroup>
          )}
        </Select>

        {showOrientation && (
          <div className="space-y-1">
            <label className="block text-sm font-medium text-slate-200">
              {t("templates.orientation")}
            </label>
            <div className="inline-flex overflow-hidden rounded-md border border-slate-700">
              <button
                type="button"
                onClick={() => setOrientation("portrait")}
                className={[
                  "px-3 py-1.5 text-xs",
                  orientation === "portrait"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-300 hover:bg-slate-800",
                ].join(" ")}
              >
                ▯ {t("templates.portrait")}
              </button>
              <button
                type="button"
                onClick={() => setOrientation("landscape")}
                className={[
                  "px-3 py-1.5 text-xs",
                  orientation === "landscape"
                    ? "bg-indigo-600 text-white"
                    : "bg-slate-900 text-slate-300 hover:bg-slate-800",
                ].join(" ")}
              >
                ▭ {t("templates.landscape")}
              </button>
            </div>
          </div>
        )}

        {isCustom && (
          <div className="grid grid-cols-2 gap-2">
            <Input
              label={t("templates.customWidthMm")}
              type="number"
              min={10}
              max={1000}
              step={1}
              value={customW}
              onChange={(e) => setCustomW(Number(e.target.value) || 0)}
            />
            <Input
              label={t("templates.customHeightMm")}
              type="number"
              min={10}
              max={1000}
              step={1}
              value={customH}
              onChange={(e) => setCustomH(Number(e.target.value) || 0)}
            />
          </div>
        )}

        {resolved && (
          <p className="rounded border border-slate-800 bg-slate-900/40 px-3 py-2 text-xs text-slate-400">
            {t("templates.resolvedSize", { w: resolved.w, h: resolved.h })}
          </p>
        )}

        {create.error && (
          <p className="text-sm text-rose-400">
            {create.error instanceof Error ? create.error.message : String(create.error)}
          </p>
        )}
      </div>
    </Modal>
  );
}
