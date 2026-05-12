/**
 * Always-visible alignment toolbar that sits between the editor's main
 * Toolbar and the 3-panel canvas layout. Two icon-button groups:
 *   - Page-relative: enabled when ≥1 object is selected.
 *   - Selection-relative: align (≥2) and distribute (≥3).
 *
 * Disabled buttons are still visible (Canva/Figma pattern) so the bar
 * doesn't pop in/out as the user clicks around.
 */

import { useTranslation } from "react-i18next";
import type { AlignMode, ZOrderMode } from "./store";
import { useEditorStore } from "./store";

type IconBtnProps = {
  symbol: string;
  title: string;
  disabled: boolean;
  onClick: () => void;
};

function IconBtn({ symbol, title, disabled, onClick }: IconBtnProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      disabled={disabled}
      title={title}
      className={[
        "flex h-7 w-7 items-center justify-center rounded text-sm",
        disabled
          ? "cursor-not-allowed text-slate-700"
          : "text-slate-300 hover:bg-slate-800 hover:text-white",
      ].join(" ")}
    >
      {symbol}
    </button>
  );
}

export function AlignmentBar() {
  const { t } = useTranslation();
  const selectedIds = useEditorStore((s) => s.selectedIds);
  const align = useEditorStore((s) => s.alignObjects);
  const reorder = useEditorStore((s) => s.reorderObjects);

  const hasOne = selectedIds.length >= 1;
  const hasTwo = selectedIds.length >= 2;
  const hasThree = selectedIds.length >= 3;

  const fire = (mode: AlignMode) => () => align(mode);
  const fireZ = (mode: ZOrderMode) => () => reorder(mode);

  return (
    <div className="flex items-center gap-2 border-b border-slate-800 bg-slate-950 px-4 py-1.5 text-xs">
      {/* Page-relative group */}
      <span className="text-[10px] uppercase tracking-wider text-slate-500">
        {t("editor.alignBar.page")}
      </span>
      <div className="flex items-center gap-0.5">
        <IconBtn
          symbol="⫷"
          title={t("editor.alignBar.pageLeft")}
          disabled={!hasOne}
          onClick={fire("page.left")}
        />
        <IconBtn
          symbol="⇔"
          title={t("editor.alignBar.pageCenterH")}
          disabled={!hasOne}
          onClick={fire("page.centerH")}
        />
        <IconBtn
          symbol="⫸"
          title={t("editor.alignBar.pageRight")}
          disabled={!hasOne}
          onClick={fire("page.right")}
        />
        <span className="mx-1 text-slate-700">·</span>
        <IconBtn
          symbol="⫶"
          title={t("editor.alignBar.pageTop")}
          disabled={!hasOne}
          onClick={fire("page.top")}
        />
        <IconBtn
          symbol="⇕"
          title={t("editor.alignBar.pageMiddleV")}
          disabled={!hasOne}
          onClick={fire("page.middleV")}
        />
        <IconBtn
          symbol="⫴"
          title={t("editor.alignBar.pageBottom")}
          disabled={!hasOne}
          onClick={fire("page.bottom")}
        />
      </div>

      <span className="mx-2 h-4 w-px bg-slate-800" />

      {/* Selection-relative group */}
      <span className="text-[10px] uppercase tracking-wider text-slate-500">
        {t("editor.alignBar.selection")}
      </span>
      <div className="flex items-center gap-0.5">
        <IconBtn
          symbol="⊣"
          title={t("editor.alignBar.selLeft")}
          disabled={!hasTwo}
          onClick={fire("sel.left")}
        />
        <IconBtn
          symbol="⊥"
          title={t("editor.alignBar.selCenterH")}
          disabled={!hasTwo}
          onClick={fire("sel.centerH")}
        />
        <IconBtn
          symbol="⊢"
          title={t("editor.alignBar.selRight")}
          disabled={!hasTwo}
          onClick={fire("sel.right")}
        />
        <span className="mx-1 text-slate-700">·</span>
        <IconBtn
          symbol="⊤"
          title={t("editor.alignBar.selTop")}
          disabled={!hasTwo}
          onClick={fire("sel.top")}
        />
        <IconBtn
          symbol="⊕"
          title={t("editor.alignBar.selMiddleV")}
          disabled={!hasTwo}
          onClick={fire("sel.middleV")}
        />
        <IconBtn
          symbol="⊥"
          title={t("editor.alignBar.selBottom")}
          disabled={!hasTwo}
          onClick={fire("sel.bottom")}
        />
        <span className="mx-1 text-slate-700">·</span>
        <IconBtn
          symbol="⇿"
          title={t("editor.alignBar.distributeH")}
          disabled={!hasThree}
          onClick={fire("sel.distributeH")}
        />
        <IconBtn
          symbol="⥯"
          title={t("editor.alignBar.distributeV")}
          disabled={!hasThree}
          onClick={fire("sel.distributeV")}
        />
      </div>

      <span className="mx-2 h-4 w-px bg-slate-800" />

      {/* Z-order (layer) group — operates on the same selection */}
      <span className="text-[10px] uppercase tracking-wider text-slate-500">
        {t("editor.alignBar.layer")}
      </span>
      <div className="flex items-center gap-0.5">
        <IconBtn
          symbol="⤓"
          title={t("editor.alignBar.toBack")}
          disabled={!hasOne}
          onClick={fireZ("back")}
        />
        <IconBtn
          symbol="↓"
          title={t("editor.alignBar.backward")}
          disabled={!hasOne}
          onClick={fireZ("backward")}
        />
        <IconBtn
          symbol="↑"
          title={t("editor.alignBar.forward")}
          disabled={!hasOne}
          onClick={fireZ("forward")}
        />
        <IconBtn
          symbol="⤒"
          title={t("editor.alignBar.toFront")}
          disabled={!hasOne}
          onClick={fireZ("front")}
        />
      </div>

      {/* Selection counter */}
      <span className="ml-auto font-mono text-[10px] text-slate-500">
        {t("editor.alignBar.selectionCount", { count: selectedIds.length })}
      </span>
    </div>
  );
}
