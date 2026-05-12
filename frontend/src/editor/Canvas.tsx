import Konva from "konva";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Layer, Rect, Stage, Transformer } from "react-konva";
import { BarcodeObject } from "./objects/BarcodeObject";
import { ImageObject } from "./objects/ImageObject";
import { LineObject } from "./objects/LineObject";
import { RectObject } from "./objects/RectObject";
import { TextObject } from "./objects/TextObject";
import { useEditorStore } from "./store";
import { fitScale } from "./units";

export function Canvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);

  const canvas = useEditorStore((s) => s.canvas);
  const selectedIds = useEditorStore((s) => s.selectedIds);
  const select = useEditorStore((s) => s.select);
  const toggleSelect = useEditorStore((s) => s.toggleSelect);
  const clearSelection = useEditorStore((s) => s.clearSelection);
  const updateObject = useEditorStore((s) => s.updateObject);

  // Translate raw click events into the right selection mutation.
  // Shift-click toggles the object in/out of the selection so users can
  // build up a multi-select for the alignment tools.
  const onObjectSelect = (id: string, e: Konva.KonvaEventObject<unknown>) => {
    if (e.evt instanceof MouseEvent && e.evt.shiftKey) {
      toggleSelect(id);
    } else {
      select(id);
    }
  };

  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

  // Measure synchronously after layout so the very first paint already
  // uses the real container size — avoids the "tiny thumbnail until
  // ResizeObserver fires" flash, especially noticeable on slow devices.
  useLayoutEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const rect = el.getBoundingClientRect();
    setContainerSize({ width: rect.width, height: rect.height });
  }, []);

  // Track container size so the canvas re-fits when the panel resizes.
  useEffect(() => {
    const el = containerRef.current;
    if (!el) return;
    const ro = new ResizeObserver(([entry]) => {
      setContainerSize({
        width: entry.contentRect.width,
        height: entry.contentRect.height,
      });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Bind transformer to the currently selected nodes (any non-zero count).
  useEffect(() => {
    const transformer = transformerRef.current;
    const stage = stageRef.current;
    if (!transformer || !stage) return;
    if (selectedIds.length === 0) {
      transformer.nodes([]);
      transformer.getLayer()?.batchDraw();
      return;
    }
    const nodes = selectedIds
      .map((id) => stage.findOne(`#${id}`))
      .filter((n): n is Konva.Node => n !== undefined);
    transformer.nodes(nodes);
    transformer.getLayer()?.batchDraw();
  }, [selectedIds, canvas]);

  // Always render the container div so the ref attaches synchronously and
  // the measurement effects (which run once on mount) see real DOM. If we
  // returned null while the canvas was loading, the very first paint would
  // measure a missing element and lock containerSize at {0, 0} — the Stage
  // would then never appear.
  const scale = canvas ? fitScale(containerSize, canvas.stage) : 0;
  const stagePxW = canvas ? canvas.stage.width_mm * scale : 0;
  const stagePxH = canvas ? canvas.stage.height_mm * scale : 0;

  return (
    <div
      ref={containerRef}
      className="relative flex min-h-0 min-w-0 flex-1 items-center justify-center overflow-hidden bg-slate-900"
    >
      {canvas && scale > 0 && (
        <Stage
          ref={stageRef}
          width={stagePxW}
          height={stagePxH}
          onMouseDown={(e) => {
            // Click on empty stage → clear selection. Shift-click on
            // empty stage is a no-op (avoids accidentally wiping a
            // partially-built selection).
            if (e.target === e.target.getStage()) {
              const isShift = e.evt instanceof MouseEvent && e.evt.shiftKey;
              if (!isShift) clearSelection();
            }
          }}
          className="shadow-2xl"
        >
          <Layer>
            {/* Paper background */}
            <Rect
              x={0}
              y={0}
              width={stagePxW}
              height={stagePxH}
              fill="white"
              stroke="#475569"
              strokeWidth={1}
            />
            {canvas.objects.map((o) => {
              if (o.type === "text") {
                return (
                  <TextObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                  />
                );
              }
              if (o.type === "rect") {
                return (
                  <RectObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                  />
                );
              }
              if (o.type === "image") {
                return (
                  <ImageObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                  />
                );
              }
              if (o.type === "line") {
                return (
                  <LineObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                  />
                );
              }
              if (o.type === "barcode") {
                return (
                  <BarcodeObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                  />
                );
              }
              return null;
            })}
            <Transformer
              ref={transformerRef}
              rotateEnabled
              keepRatio={false}
              borderStroke="#6366f1"
              anchorStroke="#6366f1"
              anchorFill="#1e293b"
            />
          </Layer>
        </Stage>
      )}
      {canvas && (
        <div className="pointer-events-none absolute bottom-2 right-3 rounded bg-slate-950/70 px-2 py-1 text-xs text-slate-400">
          {canvas.stage.width_mm} × {canvas.stage.height_mm} mm · {Math.round(scale * 100) / 100}{" "}
          px/mm
        </div>
      )}
    </div>
  );
}
