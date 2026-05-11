import Konva from "konva";
import { useEffect, useRef, useState } from "react";
import { Layer, Rect, Stage, Transformer } from "react-konva";
import { ImageObject } from "./objects/ImageObject";
import { RectObject } from "./objects/RectObject";
import { TextObject } from "./objects/TextObject";
import { useEditorStore } from "./store";
import { fitScale } from "./units";

export function Canvas() {
  const containerRef = useRef<HTMLDivElement>(null);
  const stageRef = useRef<Konva.Stage>(null);
  const transformerRef = useRef<Konva.Transformer>(null);

  const canvas = useEditorStore((s) => s.canvas);
  const selectedId = useEditorStore((s) => s.selectedId);
  const select = useEditorStore((s) => s.select);
  const updateObject = useEditorStore((s) => s.updateObject);

  const [containerSize, setContainerSize] = useState({ width: 0, height: 0 });

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

  // Bind transformer to the currently selected node.
  useEffect(() => {
    const transformer = transformerRef.current;
    const stage = stageRef.current;
    if (!transformer || !stage) return;
    if (!selectedId) {
      transformer.nodes([]);
      return;
    }
    const node = stage.findOne(`#${selectedId}`);
    if (node) {
      transformer.nodes([node]);
    } else {
      transformer.nodes([]);
    }
    transformer.getLayer()?.batchDraw();
  }, [selectedId, canvas]);

  if (!canvas) return null;

  const scale = fitScale(containerSize, canvas.stage);
  const stagePxW = canvas.stage.width_mm * scale;
  const stagePxH = canvas.stage.height_mm * scale;

  return (
    <div
      ref={containerRef}
      className="relative flex h-full w-full items-center justify-center overflow-hidden bg-slate-900"
    >
      {scale > 0 && (
        <Stage
          ref={stageRef}
          width={stagePxW}
          height={stagePxH}
          onMouseDown={(e) => {
            // Click on empty stage → deselect
            if (e.target === e.target.getStage()) select(null);
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
                    onSelect={() => select(o.id)}
                    onDragEnd={(x, y) => updateObject(o.id, { x, y })}
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
                    onSelect={() => select(o.id)}
                    onDragEnd={(x, y) => updateObject(o.id, { x, y })}
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
                    onSelect={() => select(o.id)}
                    onDragEnd={(x, y) => updateObject(o.id, { x, y })}
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
      <div className="pointer-events-none absolute bottom-2 right-3 rounded bg-slate-950/70 px-2 py-1 text-xs text-slate-400">
        {canvas.stage.width_mm} × {canvas.stage.height_mm} mm · {Math.round(scale * 100) / 100}{" "}
        px/mm
      </div>
    </div>
  );
}
