import { useTranslation } from "react-i18next";
import { Input } from "../components/ui/Input";
import { Select } from "../components/ui/Select";
import { Button } from "../components/ui/Button";
import { useEditorStore } from "./store";
import type { EditorObject, ImageObject, RectObject, TextObject } from "./types";

export function RightPanel() {
  const { t } = useTranslation();
  const canvas = useEditorStore((s) => s.canvas);
  const selectedId = useEditorStore((s) => s.selectedId);
  const updateObject = useEditorStore((s) => s.updateObject);
  const deleteObject = useEditorStore((s) => s.deleteObject);

  const selected = canvas?.objects.find((o) => o.id === selectedId) ?? null;

  return (
    <aside className="w-72 shrink-0 space-y-4 overflow-y-auto border-l border-slate-800 bg-slate-950 p-4">
      <h3 className="text-xs font-semibold uppercase tracking-wider text-slate-500">
        {t("editor.properties")}
      </h3>

      {!selected && <p className="text-sm text-slate-500">{t("editor.selectToEdit")}</p>}

      {selected && (
        <>
          <CommonProps obj={selected} update={(p) => updateObject(selected.id, p)} />
          {selected.type === "text" && (
            <TextProps obj={selected} update={(p) => updateObject(selected.id, p)} />
          )}
          {selected.type === "rect" && (
            <RectProps obj={selected} update={(p) => updateObject(selected.id, p)} />
          )}
          {selected.type === "image" && (
            <ImageProps obj={selected} update={(p) => updateObject(selected.id, p)} />
          )}

          <div className="pt-3">
            <Button variant="danger" className="w-full" onClick={() => deleteObject(selected.id)}>
              {t("common.delete")}
            </Button>
          </div>
        </>
      )}
    </aside>
  );
}

function CommonProps({
  obj,
  update,
}: {
  obj: EditorObject;
  update: (p: Partial<EditorObject>) => void;
}) {
  return (
    <div className="grid grid-cols-2 gap-2">
      <NumberInput label="X (mm)" value={obj.x} onChange={(x) => update({ x })} />
      <NumberInput label="Y (mm)" value={obj.y} onChange={(y) => update({ y })} />
      <NumberInput
        label="↻ (°)"
        value={obj.rotation ?? 0}
        onChange={(rotation) => update({ rotation })}
      />
    </div>
  );
}

function TextProps({ obj, update }: { obj: TextObject; update: (p: Partial<TextObject>) => void }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3 border-t border-slate-800 pt-3">
      <div>
        <label className="mb-1 block text-sm font-medium text-slate-200">
          {t("editor.textValue")}
        </label>
        <textarea
          value={obj.text}
          rows={3}
          onChange={(e) => update({ text: e.target.value })}
          className="block w-full rounded-md border border-slate-700 bg-slate-900 px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-indigo-400"
        />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <NumberInput
          label={t("editor.fontSizeMm")}
          step={0.5}
          min={0.5}
          value={obj.fontSize}
          onChange={(fontSize) => update({ fontSize })}
        />
        <ColorInput
          label={t("editor.fill")}
          value={obj.fill}
          onChange={(fill) => update({ fill })}
        />
      </div>
      <Select
        label={t("editor.fontFamily")}
        value={obj.fontFamily}
        onChange={(e) => update({ fontFamily: e.target.value })}
      >
        <option value="Inter, sans-serif">Inter (sans)</option>
        <option value="Arial, sans-serif">Arial</option>
        <option value="Helvetica, sans-serif">Helvetica</option>
        <option value="Times New Roman, serif">Times New Roman</option>
        <option value="Georgia, serif">Georgia</option>
        <option value="Courier New, monospace">Courier New</option>
      </Select>
      <div className="grid grid-cols-2 gap-2">
        <Select
          label={t("editor.bold")}
          value={obj.fontWeight ?? "normal"}
          onChange={(e) => update({ fontWeight: e.target.value as "normal" | "bold" })}
        >
          <option value="normal">{t("editor.normal")}</option>
          <option value="bold">{t("editor.boldYes")}</option>
        </Select>
        <Select
          label={t("editor.italic")}
          value={obj.fontStyle ?? "normal"}
          onChange={(e) => update({ fontStyle: e.target.value as "normal" | "italic" })}
        >
          <option value="normal">{t("editor.normal")}</option>
          <option value="italic">{t("editor.italicYes")}</option>
        </Select>
      </div>
      <Select
        label={t("editor.align")}
        value={obj.align ?? "left"}
        onChange={(e) => update({ align: e.target.value as "left" | "center" | "right" })}
      >
        <option value="left">{t("editor.alignLeft")}</option>
        <option value="center">{t("editor.alignCenter")}</option>
        <option value="right">{t("editor.alignRight")}</option>
      </Select>
    </div>
  );
}

function RectProps({ obj, update }: { obj: RectObject; update: (p: Partial<RectObject>) => void }) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3 border-t border-slate-800 pt-3">
      <div className="grid grid-cols-2 gap-2">
        <NumberInput
          label={t("editor.widthMm")}
          step={0.5}
          min={0.1}
          value={obj.width}
          onChange={(width) => update({ width })}
        />
        <NumberInput
          label={t("editor.heightMm")}
          step={0.5}
          min={0.1}
          value={obj.height}
          onChange={(height) => update({ height })}
        />
        <ColorInput
          label={t("editor.fill")}
          value={obj.fill}
          onChange={(fill) => update({ fill })}
        />
        <ColorInput
          label={t("editor.stroke")}
          value={obj.stroke ?? "#000000"}
          onChange={(stroke) => update({ stroke })}
        />
        <NumberInput
          label={t("editor.strokeMm")}
          step={0.05}
          min={0}
          value={obj.strokeWidth ?? 0}
          onChange={(strokeWidth) => update({ strokeWidth })}
        />
      </div>
    </div>
  );
}

function ImageProps({
  obj,
  update,
}: {
  obj: ImageObject;
  update: (p: Partial<ImageObject>) => void;
}) {
  const { t } = useTranslation();
  return (
    <div className="space-y-3 border-t border-slate-800 pt-3">
      <div className="grid grid-cols-2 gap-2">
        <NumberInput
          label={t("editor.widthMm")}
          step={0.5}
          min={1}
          value={obj.width}
          onChange={(width) => update({ width })}
        />
        <NumberInput
          label={t("editor.heightMm")}
          step={0.5}
          min={1}
          value={obj.height}
          onChange={(height) => update({ height })}
        />
      </div>
      <p className="text-xs text-slate-500">asset #{obj.assetId}</p>
    </div>
  );
}

function NumberInput({
  label,
  value,
  onChange,
  step = 0.5,
  min,
}: {
  label: string;
  value: number;
  onChange: (v: number) => void;
  step?: number;
  min?: number;
}) {
  return (
    <Input
      label={label}
      type="number"
      step={step}
      min={min}
      value={Number.isFinite(value) ? Math.round(value * 100) / 100 : 0}
      onChange={(e) => {
        const n = Number(e.target.value);
        if (!Number.isNaN(n)) onChange(n);
      }}
    />
  );
}

function ColorInput({
  label,
  value,
  onChange,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div className="space-y-1">
      <label className="block text-sm font-medium text-slate-200">{label}</label>
      <input
        type="color"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-9 w-full cursor-pointer rounded-md border border-slate-700 bg-slate-900"
      />
    </div>
  );
}
