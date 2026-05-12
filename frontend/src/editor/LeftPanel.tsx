import { useRef } from "react";
import { useTranslation } from "react-i18next";
import { useUploadAsset } from "../hooks/useAssets";
import { Button } from "../components/ui/Button";
import { newObjectId, useEditorStore } from "./store";

export function LeftPanel() {
  const { t } = useTranslation();
  const addObject = useEditorStore((s) => s.addObject);
  const canvas = useEditorStore((s) => s.canvas);
  const upload = useUploadAsset();
  const fileRef = useRef<HTMLInputElement>(null);

  if (!canvas) return null;

  const centerX = canvas.stage.width_mm / 2;
  const centerY = canvas.stage.height_mm / 2;

  return (
    <aside className="w-56 shrink-0 space-y-2 border-r border-slate-800 bg-slate-950 p-3">
      <h3 className="px-2 text-xs font-semibold uppercase tracking-wider text-slate-500">
        {t("editor.add")}
      </h3>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() =>
          addObject({
            id: newObjectId(),
            type: "text",
            x: Math.max(2, centerX - 20),
            y: Math.max(2, centerY - 4),
            text: t("editor.newText"),
            fontSize: 6,
            fontFamily: "Inter, sans-serif",
            fill: "#0f172a",
          })
        }
      >
        T &nbsp; {t("editor.text")}
      </Button>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() => {
          const w = Math.max(20, Math.min(60, canvas.stage.width_mm * 0.4));
          const h = Math.max(10, Math.min(30, canvas.stage.height_mm * 0.15));
          addObject({
            id: newObjectId(),
            type: "text",
            x: Math.max(2, centerX - w / 2),
            y: Math.max(2, centerY - h / 2),
            text: t("editor.textBlockSample"),
            fontSize: 5,
            fontFamily: "Inter, sans-serif",
            fill: "#0f172a",
            width: w,
            height: h,
            autoFit: true,
            minFontSize: 2,
            maxFontSize: 8,
          });
        }}
      >
        ¶ &nbsp; {t("editor.textBlock")}
      </Button>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() =>
          addObject({
            id: newObjectId(),
            type: "rect",
            x: Math.max(2, centerX - 15),
            y: Math.max(2, centerY - 10),
            width: 30,
            height: 20,
            fill: "#94a3b8",
            stroke: "#0f172a",
            strokeWidth: 0.3,
          })
        }
      >
        ▭ &nbsp; {t("editor.rect")}
      </Button>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() =>
          addObject({
            id: newObjectId(),
            type: "line",
            x: Math.max(2, centerX - 15),
            y: Math.max(2, centerY),
            points: [0, 0, 30, 0],
            stroke: "#0f172a",
            strokeWidth: 0.3,
          })
        }
      >
        ╱ &nbsp; {t("editor.line")}
      </Button>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() =>
          addObject({
            id: newObjectId(),
            type: "barcode",
            x: Math.max(2, centerX - 25),
            y: Math.max(2, centerY - 10),
            width: 50,
            height: 20,
            barcodeType: "ean13",
            data: "590123456789",
          })
        }
      >
        ▤ &nbsp; {t("editor.barcode")}
      </Button>

      <Button
        variant="secondary"
        className="w-full justify-start"
        onClick={() => fileRef.current?.click()}
        disabled={upload.isPending}
      >
        🖼 &nbsp; {upload.isPending ? t("common.loading") : t("editor.image")}
      </Button>
      <input
        ref={fileRef}
        type="file"
        accept="image/png,image/jpeg,image/svg+xml"
        className="hidden"
        onChange={async (e) => {
          const file = e.target.files?.[0];
          if (!file) return;
          try {
            const asset = await upload.mutateAsync(file);
            // Best-fit scale: shrink large images so they fit on the canvas
            const maxMm = Math.min(canvas.stage.width_mm * 0.6, canvas.stage.height_mm * 0.6);
            const ratio = asset.width_px / Math.max(asset.height_px, 1);
            const widthMm = Math.min(maxMm, ratio >= 1 ? maxMm : maxMm * ratio);
            const heightMm = widthMm / ratio;
            addObject({
              id: newObjectId(),
              type: "image",
              x: Math.max(2, (canvas.stage.width_mm - widthMm) / 2),
              y: Math.max(2, (canvas.stage.height_mm - heightMm) / 2),
              width: widthMm,
              height: heightMm,
              assetId: asset.id,
            });
          } finally {
            // Allow re-selecting the same file
            e.target.value = "";
          }
        }}
      />

      {upload.error && (
        <p className="px-1 text-xs text-rose-400">
          {upload.error instanceof Error ? upload.error.message : String(upload.error)}
        </p>
      )}
    </aside>
  );
}
