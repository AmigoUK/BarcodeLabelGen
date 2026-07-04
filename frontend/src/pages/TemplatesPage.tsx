import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useNavigate } from "react-router-dom";
import { ImportTemplateModal } from "../components/ImportTemplateModal";
import { Button } from "../components/ui/Button";
import { Input } from "../components/ui/Input";
import { Modal } from "../components/ui/Modal";
import { Select } from "../components/ui/Select";
import {
  type TemplateSummary,
  exportTemplateToFile,
  useCreateTemplate,
  useDeleteTemplate,
  useLabelFormats,
  useTemplates,
  useUpdateTemplate,
} from "../hooks/useTemplates";
import {
  useCreateFolder,
  useDeleteFolder,
  useFolders,
  useRenameFolder,
} from "../hooks/useFolders";

type FolderFilter = "all" | "none" | number;

export function TemplatesPage() {
  const { t } = useTranslation();
  const [folderFilter, setFolderFilter] = useState<FolderFilter>("all");
  const templates = useTemplates(folderFilter === "all" ? undefined : folderFilter);
  const del = useDeleteTemplate();
  const [showCreate, setShowCreate] = useState(false);
  const [showImport, setShowImport] = useState(false);
  const [settingsFor, setSettingsFor] = useState<TemplateSummary | null>(null);
  const [query, setQuery] = useState("");

  const filtered = templates.data
    ? query.trim()
      ? templates.data.filter((tpl) => tpl.name.toLowerCase().includes(query.trim().toLowerCase()))
      : templates.data
    : [];

  return (
    <div className="flex gap-6">
      <FolderRail active={folderFilter} onSelect={setFolderFilter} />

      <div className="min-w-0 flex-1 space-y-6">
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
          <Button variant="secondary" onClick={() => setShowImport(true)}>
            ⬆ {t("templates.import")}
          </Button>
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
              <h3 className="mb-1 truncate font-semibold text-slate-100">
                {tpl.is_shared && (
                  <span className="mr-1" title={t("templates.sharedBadge")}>
                    📚
                  </span>
                )}
                {tpl.name}
              </h3>
              <p className="text-xs text-slate-500">
                {tpl.width_mm} × {tpl.height_mm} mm
              </p>
              {tpl.description && (
                <p className="mt-2 line-clamp-2 text-sm text-slate-400">{tpl.description}</p>
              )}
              <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>v{tpl.version}</span>
                <span>{new Date(tpl.updated_at).toLocaleDateString()}</span>
                <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100">
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      setSettingsFor(tpl);
                    }}
                    className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                    aria-label={t("templates.settings")}
                    title={t("templates.settingsTooltip")}
                  >
                    ⚙
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      const safe =
                        tpl.name.replace(/[^A-Za-z0-9._-]+/g, "_").replace(/^_|_$/g, "") ||
                        "template";
                      void exportTemplateToFile(tpl.id, `${safe}.blg-template.json`);
                    }}
                    className="rounded px-1.5 py-0.5 text-slate-400 hover:bg-slate-800 hover:text-slate-100"
                    aria-label={t("templates.export")}
                    title={t("templates.exportTooltip")}
                  >
                    ⬇
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.preventDefault();
                      if (confirm(t("templates.confirmDelete", { name: tpl.name }))) {
                        del.mutate(tpl.id);
                      }
                    }}
                    className="rounded px-1.5 py-0.5 text-rose-400 hover:bg-rose-950/50"
                    aria-label={t("common.delete")}
                  >
                    ✕
                  </button>
                </div>
              </div>
            </a>
          ))}
        </div>
      )}

      {showCreate && <NewTemplateModal onClose={() => setShowCreate(false)} />}
      {showImport && <ImportTemplateModal onClose={() => setShowImport(false)} />}
      {settingsFor && (
        <TemplateSettingsModal template={settingsFor} onClose={() => setSettingsFor(null)} />
      )}
      </div>
    </div>
  );
}

function FolderRail({
  active,
  onSelect,
}: {
  active: FolderFilter;
  onSelect: (f: FolderFilter) => void;
}) {
  const { t } = useTranslation();
  const folders = useFolders();
  const createFolder = useCreateFolder();
  const renameFolder = useRenameFolder();
  const deleteFolder = useDeleteFolder();
  const [newName, setNewName] = useState("");
  const [adding, setAdding] = useState(false);

  const item = (key: FolderFilter, label: string, count?: number | null) => (
    <button
      type="button"
      onClick={() => onSelect(key)}
      className={[
        "group/f flex w-full items-center justify-between rounded px-2 py-1.5 text-left text-sm",
        active === key ? "bg-indigo-600 text-white" : "text-slate-300 hover:bg-slate-800",
      ].join(" ")}
    >
      <span className="truncate">📁 {label}</span>
      <span className="flex items-center gap-1">
        {typeof key === "number" && (
          <span className="hidden gap-0.5 group-hover/f:flex">
            <span
              role="button"
              tabIndex={0}
              title={t("folders.rename")}
              className="rounded px-1 hover:bg-slate-700"
              onClick={(e) => {
                e.stopPropagation();
                const name = window.prompt(t("folders.renamePrompt"), label);
                if (name?.trim()) renameFolder.mutate({ id: key, name: name.trim() });
              }}
            >
              ✎
            </span>
            <span
              role="button"
              tabIndex={0}
              title={t("common.delete")}
              className="rounded px-1 text-rose-400 hover:bg-rose-950/60"
              onClick={(e) => {
                e.stopPropagation();
                if (window.confirm(t("folders.confirmDelete", { name: label }))) {
                  deleteFolder.mutate(key);
                  if (active === key) onSelect("all");
                }
              }}
            >
              ✕
            </span>
          </span>
        )}
        {count != null && <span className="text-xs opacity-70">{count}</span>}
      </span>
    </button>
  );

  return (
    <aside className="w-52 shrink-0 space-y-1">
      <h2 className="px-2 pb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {t("folders.title")}
      </h2>
      {item("all", t("folders.all"))}
      {folders.data?.map((f) => item(f.id, f.name, f.template_count))}
      {item("none", t("folders.unfiled"))}
      {adding ? (
        <form
          className="flex gap-1 px-1 pt-1"
          onSubmit={(e) => {
            e.preventDefault();
            if (!newName.trim()) return;
            createFolder.mutate(newName.trim(), {
              onSuccess: () => {
                setNewName("");
                setAdding(false);
              },
            });
          }}
        >
          <input
            autoFocus
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && setAdding(false)}
            placeholder={t("folders.namePlaceholder")}
            className="w-full rounded border border-slate-700 bg-slate-900 px-2 py-1 text-sm text-slate-100"
          />
          <Button type="submit" className="!px-2 !py-1 text-xs">
            ✓
          </Button>
        </form>
      ) : (
        <button
          type="button"
          onClick={() => setAdding(true)}
          className="w-full rounded px-2 py-1.5 text-left text-sm text-indigo-400 hover:bg-slate-800"
        >
          + {t("folders.new")}
        </button>
      )}
      {createFolder.error && (
        <p className="px-2 text-xs text-rose-400">{t("folders.errors.nameTaken")}</p>
      )}
    </aside>
  );
}

function TemplateSettingsModal({
  template,
  onClose,
}: {
  template: TemplateSummary;
  onClose: () => void;
}) {
  const { t } = useTranslation();
  const folders = useFolders();
  const update = useUpdateTemplate();
  const [folderId, setFolderId] = useState<number | "">(template.folder_id ?? "");
  const [shared, setShared] = useState(template.is_shared);

  return (
    <Modal
      open
      onClose={onClose}
      title={`${t("templates.settingsTitle")} — ${template.name}`}
      footer={
        <>
          <Button variant="secondary" onClick={onClose}>
            {t("common.cancel")}
          </Button>
          <Button
            disabled={update.isPending}
            onClick={() =>
              update.mutate(
                {
                  id: template.id,
                  patch: {
                    folder_id: folderId === "" ? null : folderId,
                    is_shared: shared,
                  },
                },
                { onSuccess: onClose },
              )
            }
          >
            {t("common.save")}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <Select
          label={t("folders.moveTo")}
          value={folderId}
          onChange={(e) => setFolderId(e.target.value === "" ? "" : Number(e.target.value))}
        >
          <option value="">— {t("folders.unfiled")} —</option>
          {folders.data?.map((f) => (
            <option key={f.id} value={f.id}>
              {f.name}
            </option>
          ))}
        </Select>
        <label className="flex cursor-pointer items-start gap-2 text-sm text-slate-200">
          <input
            type="checkbox"
            checked={shared}
            onChange={(e) => setShared(e.target.checked)}
            className="mt-0.5 h-4 w-4 rounded border-slate-700 bg-slate-900 text-indigo-600"
          />
          <span>
            📚 {t("templates.shareToggle")}
            <span className="block text-xs text-slate-500">{t("templates.shareHint")}</span>
          </span>
        </label>
        {update.error && <p className="text-sm text-rose-400">{t("auth.errors.generic")}</p>}
      </div>
    </Modal>
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
