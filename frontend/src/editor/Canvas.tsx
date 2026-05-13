import Konva from "konva";
import { useEffect, useLayoutEffect, useRef, useState } from "react";
import { Layer, Rect, Stage, Transformer } from "react-konva";
import { BarcodeObject } from "./objects/BarcodeObject";
import { ImageObject } from "./objects/ImageObject";
import { LineObject } from "./objects/LineObject";
import { RectObject } from "./objects/RectObject";
import { TextObject } from "./objects/TextObject";
import { newObjectId, useEditorStore } from "./store";
import type { EditorObject } from "./types";
import { fitScale } from "./units";

/** Transient state for an in-flight Alt+drag gesture.
 *  Lives in a ref (not the store) because it's UI-only — never persisted,
 *  never undoable. One pending-clones buffer per gesture; flushed in a
 *  single rAF so a multi-select Alt+drag is one undo step. */
type AltDragSnapshot = {
  active: boolean;
  /** Source positions in mm, keyed by object id. Set on drag-start of
   *  whichever node the user clicked; we snapshot every selected id so
   *  Konva's Transformer-driven multi-drag can be cloned wholesale. */
  positions: Map<string, { x: number; y: number }>;
  /** Clones accumulated by per-object onDragEnd, flushed together. */
  pendingClones: EditorObject[];
  flushScheduled: boolean;
};

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
  const addObjects = useEditorStore((s) => s.addObjects);
  const selectMany = useEditorStore((s) => s.selectMany);

  // Per-gesture Alt+drag state. Reset after each rAF flush.
  const altDragRef = useRef<AltDragSnapshot>({
    active: false,
    positions: new Map(),
    pendingClones: [],
    flushScheduled: false,
  });

  const handleAltDragStart = (obj: EditorObject, e: Konva.KonvaEventObject<DragEvent>) => {
    // Honour Alt only at drag start — releasing Alt mid-drag still duplicates,
    // pressing Alt mid-drag does not (matches Figma).
    if (!e.evt?.altKey) return;
    if (!canvas) return;
    const ref = altDragRef.current;
    ref.active = true;
    ref.positions.clear();
    // Snapshot every selected node's start position. Konva's Transformer
    // drags them together; each will fire its own onDragEnd which we use to
    // build one clone per source.
    const seen = new Set<string>();
    for (const id of selectedIds) {
      const target = canvas.objects.find((o) => o.id === id);
      if (target) {
        ref.positions.set(id, { x: target.x, y: target.y });
        seen.add(id);
      }
    }
    if (!seen.has(obj.id)) {
      // Alt+drag on a non-selected object — operate on just that one.
      ref.positions.set(obj.id, { x: obj.x, y: obj.y });
    }
  };

  const flushAltDrag = () => {
    const ref = altDragRef.current;
    if (ref.pendingClones.length > 0) {
      const ids = ref.pendingClones.map((c) => c.id);
      addObjects(ref.pendingClones);
      selectMany(ids); // explicit — addObjects already does this, but pin it
    }
    ref.active = false;
    ref.positions.clear();
    ref.pendingClones = [];
    ref.flushScheduled = false;
  };

  const handleDragEnd = (
    obj: EditorObject,
    patch: { x: number; y: number },
    e: Konva.KonvaEventObject<DragEvent>,
  ) => {
    const ref = altDragRef.current;
    if (!ref.active) {
      // Plain drag — commit the new position the way we always did.
      updateObject(obj.id, patch);
      return;
    }
    const original = ref.positions.get(obj.id);
    if (!original) {
      // Source wasn't part of the snapshotted set — treat as normal drag.
      updateObject(obj.id, patch);
      return;
    }
    // Build a clone at the drop position.
    ref.pendingClones.push({
      ...obj,
      id: newObjectId(),
      x: patch.x,
      y: patch.y,
    } as EditorObject);
    // Snap the source's Konva node back to its starting screen position so
    // it visibly stays put. The store position never updated, so on the
    // next React render the node would already be back here anyway — but
    // setting position() now avoids a one-frame flicker.
    e.target.position({ x: original.x * scale, y: original.y * scale });
    if (!ref.flushScheduled) {
      ref.flushScheduled = true;
      requestAnimationFrame(flushAltDrag);
    }
  };

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
  // Locked objects are filtered out — they can be selected (so the right
  // panel can offer "Unlock") but get no resize/rotate handles.
  useEffect(() => {
    const transformer = transformerRef.current;
    const stage = stageRef.current;
    if (!transformer || !stage) return;
    if (selectedIds.length === 0 || !canvas) {
      transformer.nodes([]);
      transformer.getLayer()?.batchDraw();
      return;
    }
    const lockedIds = new Set(canvas.objects.filter((o) => o.locked === true).map((o) => o.id));
    const nodes = selectedIds
      .filter((id) => !lockedIds.has(id))
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
              // Shared drag handlers — Canvas decides whether to commit the
              // move (plain drag) or queue a clone (Alt+drag).
              const onDragStart = (e: Konva.KonvaEventObject<DragEvent>) =>
                handleAltDragStart(o, e);
              const onDragMoved = (
                patch: { x: number; y: number },
                e: Konva.KonvaEventObject<DragEvent>,
              ) => handleDragEnd(o, patch, e);
              if (o.type === "text") {
                return (
                  <TextObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable={!o.locked}
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                    onDragStart={onDragStart}
                    onDragMoved={onDragMoved}
                  />
                );
              }
              if (o.type === "rect") {
                return (
                  <RectObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable={!o.locked}
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                    onDragStart={onDragStart}
                    onDragMoved={onDragMoved}
                  />
                );
              }
              if (o.type === "image") {
                return (
                  <ImageObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable={!o.locked}
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                    onDragStart={onDragStart}
                    onDragMoved={onDragMoved}
                  />
                );
              }
              if (o.type === "line") {
                return (
                  <LineObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable={!o.locked}
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                    onDragStart={onDragStart}
                    onDragMoved={onDragMoved}
                  />
                );
              }
              if (o.type === "barcode") {
                return (
                  <BarcodeObject
                    key={o.id}
                    object={o}
                    scale={scale}
                    draggable={!o.locked}
                    onSelect={(e) => onObjectSelect(o.id, e)}
                    onChange={(patch) => updateObject(o.id, patch)}
                    onDragStart={onDragStart}
                    onDragMoved={onDragMoved}
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
