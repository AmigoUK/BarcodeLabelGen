/**
 * Zustand store for the editor — single source of truth for the canvas
 * being edited. Keeps the `dirty` flag updated so autosave / save buttons
 * can react. Save/load round-trips happen through hooks (TanStack Query),
 * which call into here via `setCanvas`.
 *
 * History stack is bounded (50 snapshots) — plenty for human edit volume,
 * trivial memory cost for typical templates (a few KB each).
 */

import { create } from "zustand";
import type { CanvasData, EditorObject } from "./types";
import { type BoundsMm, getBoundsMm } from "./units";

const HISTORY_LIMIT = 50;

export type AlignMode =
  | "page.left"
  | "page.centerH"
  | "page.right"
  | "page.top"
  | "page.middleV"
  | "page.bottom"
  | "sel.left"
  | "sel.centerH"
  | "sel.right"
  | "sel.top"
  | "sel.middleV"
  | "sel.bottom"
  | "sel.distributeH"
  | "sel.distributeV";

export type ZOrderMode = "front" | "forward" | "backward" | "back";

type State = {
  canvas: CanvasData | null;
  /** ids of currently selected objects; empty array = nothing selected */
  selectedIds: string[];
  /** true when the canvas differs from what the server last saw */
  dirty: boolean;
  /** previous canvas snapshots (most recent first), capped at HISTORY_LIMIT */
  past: CanvasData[];
  future: CanvasData[];

  // --- mutations ---
  setCanvas: (c: CanvasData) => void;
  /** Replace the whole canvas as an undoable, dirty-marking edit — used by
   *  ZPL import, which swaps in a freshly parsed tree the user then saves. */
  replaceCanvas: (c: CanvasData) => void;
  markClean: () => void;

  /** Replace the entire selection with this object (or clear if null). */
  select: (id: string | null) => void;
  /** Add or remove the id from the current selection (Shift-click). */
  toggleSelect: (id: string) => void;
  /** Replace the entire selection with the given list. */
  selectMany: (ids: string[]) => void;
  /** Drop everything from the selection. */
  clearSelection: () => void;

  addObject: (o: EditorObject) => void;
  /** Bulk-add many objects in one history step + select them as a group.
   *  Used by Alt+drag (which queues a clone per dragged node and flushes
   *  the whole batch in one rAF) and any future "paste many" flow. */
  addObjects: (list: EditorObject[]) => void;
  updateObject: (id: string, patch: Partial<EditorObject>) => void;
  deleteObject: (id: string) => void;

  /** Clone every currently-selected object with an optional mm offset.
   *  New ids; every other field (font, fill, assetId, locked, printable,
   *  rotation, …) carries over verbatim. Selection moves to the clones
   *  so a follow-up Ctrl+D stacks neatly. Returns the new ids. */
  duplicateSelected: (offset?: { dx: number; dy: number }) => string[];

  /** Apply an alignment mode to the current selection in one undo step. */
  alignObjects: (mode: AlignMode) => void;

  /** Reorder selected objects in the z-stack (array order =
   *  back-to-front). One undoable step regardless of selection size;
   *  multi-select preserves the relative order of selected items. */
  reorderObjects: (mode: ZOrderMode) => void;

  undo: () => void;
  redo: () => void;
};

const pushHistory = (past: CanvasData[], snapshot: CanvasData): CanvasData[] => {
  const next = [snapshot, ...past];
  return next.length > HISTORY_LIMIT ? next.slice(0, HISTORY_LIMIT) : next;
};

/** Reorder objects in the z-stack (array index 0 = bottom-most, last
 *  = top-most). Multi-select keeps the relative order of selected
 *  items intact (Canva/Figma convention). Returns the input array
 *  unchanged when the operation is a no-op (already at the edge), so
 *  the store can avoid pushing a useless history entry. */
function computeReordered<T extends { id: string }>(
  objects: T[],
  selectedIds: string[],
  mode: ZOrderMode,
): T[] {
  const selectedSet = new Set(selectedIds);
  const selected = objects.filter((o) => selectedSet.has(o.id));
  if (selected.length === 0) return objects;
  const others = objects.filter((o) => !selectedSet.has(o.id));

  if (mode === "front") {
    // Already at the top? (every selected occupies the tail)
    const tail = objects.slice(objects.length - selected.length);
    if (tail.every((o) => selectedSet.has(o.id))) return objects;
    return [...others, ...selected];
  }
  if (mode === "back") {
    const head = objects.slice(0, selected.length);
    if (head.every((o) => selectedSet.has(o.id))) return objects;
    return [...selected, ...others];
  }

  // forward / backward — single-step swap, group-aware: move each
  // selected past the next non-selected neighbour, preserving the
  // selection's internal cohesion.
  const result = [...objects];
  if (mode === "forward") {
    // Walk right-to-left so a swap doesn't double-process the same item.
    for (let i = result.length - 1; i >= 0; i--) {
      if (
        selectedSet.has(result[i].id) &&
        i + 1 < result.length &&
        !selectedSet.has(result[i + 1].id)
      ) {
        [result[i], result[i + 1]] = [result[i + 1], result[i]];
      }
    }
  } else {
    // backward: walk left-to-right
    for (let i = 0; i < result.length; i++) {
      if (selectedSet.has(result[i].id) && i - 1 >= 0 && !selectedSet.has(result[i - 1].id)) {
        [result[i], result[i - 1]] = [result[i - 1], result[i]];
      }
    }
  }
  // Detect no-op (everyone was already at the requested edge)
  const changed = result.some((o, i) => o.id !== objects[i].id);
  return changed ? result : objects;
}

/** Compute new x/y for each object so the alignment mode is satisfied.
 *  Returns a Map<id, {x, y}> — caller maps it onto canvas.objects. */
function computeAlignedPositions(
  objects: EditorObject[],
  selectedIds: string[],
  stage: { width_mm: number; height_mm: number },
  mode: AlignMode,
): Map<string, { x: number; y: number }> {
  const result = new Map<string, { x: number; y: number }>();
  const selected = objects.filter((o) => selectedIds.includes(o.id));
  if (selected.length === 0) return result;
  const bounds: { id: string; b: BoundsMm }[] = selected.map((o) => ({
    id: o.id,
    b: getBoundsMm(o),
  }));

  // Page-relative — operate per object independently
  if (mode.startsWith("page.")) {
    for (const { id, b } of bounds) {
      const obj = objects.find((o) => o.id === id)!;
      let nx = obj.x;
      let ny = obj.y;
      // The object's stored x/y is its top-left. Bounds derived above
      // may shift slightly (line: anchor + min point offset). Treat the
      // bounds as the source of truth and compute the delta to apply
      // to obj.x / obj.y.
      const dx = obj.x - b.x;
      const dy = obj.y - b.y;
      switch (mode) {
        case "page.left":
          nx = 0 + dx;
          break;
        case "page.centerH":
          nx = (stage.width_mm - b.w) / 2 + dx;
          break;
        case "page.right":
          nx = stage.width_mm - b.w + dx;
          break;
        case "page.top":
          ny = 0 + dy;
          break;
        case "page.middleV":
          ny = (stage.height_mm - b.h) / 2 + dy;
          break;
        case "page.bottom":
          ny = stage.height_mm - b.h + dy;
          break;
      }
      result.set(id, { x: nx, y: ny });
    }
    return result;
  }

  // Selection-relative — needs the bounding box of the selection
  const selMinX = Math.min(...bounds.map((b) => b.b.x));
  const selMaxX = Math.max(...bounds.map((b) => b.b.x + b.b.w));
  const selMinY = Math.min(...bounds.map((b) => b.b.y));
  const selMaxY = Math.max(...bounds.map((b) => b.b.y + b.b.h));
  const selCenterX = (selMinX + selMaxX) / 2;
  const selCenterY = (selMinY + selMaxY) / 2;

  if (
    mode === "sel.left" ||
    mode === "sel.centerH" ||
    mode === "sel.right" ||
    mode === "sel.top" ||
    mode === "sel.middleV" ||
    mode === "sel.bottom"
  ) {
    for (const { id, b } of bounds) {
      const obj = objects.find((o) => o.id === id)!;
      const dx = obj.x - b.x;
      const dy = obj.y - b.y;
      let nx = obj.x;
      let ny = obj.y;
      switch (mode) {
        case "sel.left":
          nx = selMinX + dx;
          break;
        case "sel.centerH":
          nx = selCenterX - b.w / 2 + dx;
          break;
        case "sel.right":
          nx = selMaxX - b.w + dx;
          break;
        case "sel.top":
          ny = selMinY + dy;
          break;
        case "sel.middleV":
          ny = selCenterY - b.h / 2 + dy;
          break;
        case "sel.bottom":
          ny = selMaxY - b.h + dy;
          break;
      }
      result.set(id, { x: nx, y: ny });
    }
    return result;
  }

  // Distribute (≥3 objects). Outer two stay; middle ones get equal gaps.
  if (mode === "sel.distributeH" || mode === "sel.distributeV") {
    if (bounds.length < 3) return result; // no-op

    const horizontal = mode === "sel.distributeH";
    const sorted = [...bounds].sort((a, b) => (horizontal ? a.b.x - b.b.x : a.b.y - b.b.y));
    const first = sorted[0];
    const last = sorted[sorted.length - 1];
    const totalSize = sorted.reduce((acc, s) => acc + (horizontal ? s.b.w : s.b.h), 0);
    const span = horizontal ? last.b.x + last.b.w - first.b.x : last.b.y + last.b.h - first.b.y;
    const totalGap = span - totalSize;
    const gap = totalGap / (sorted.length - 1);

    let cursor = horizontal ? first.b.x : first.b.y;
    for (const item of sorted) {
      const obj = objects.find((o) => o.id === item.id)!;
      const dx = obj.x - item.b.x;
      const dy = obj.y - item.b.y;
      if (horizontal) {
        result.set(item.id, { x: cursor + dx, y: obj.y });
        cursor += item.b.w + gap;
      } else {
        result.set(item.id, { x: obj.x, y: cursor + dy });
        cursor += item.b.h + gap;
      }
    }
  }

  return result;
}

export const useEditorStore = create<State>((set) => ({
  canvas: null,
  selectedIds: [],
  dirty: false,
  past: [],
  future: [],

  setCanvas: (c) =>
    set({
      canvas: c,
      selectedIds: [],
      dirty: false,
      past: [],
      future: [],
    }),

  replaceCanvas: (c) =>
    set((s) => ({
      canvas: c,
      selectedIds: [],
      dirty: true,
      past: s.canvas ? pushHistory(s.past, s.canvas) : s.past,
      future: [],
    })),

  markClean: () => set({ dirty: false }),

  select: (id) => set({ selectedIds: id === null ? [] : [id] }),

  toggleSelect: (id) =>
    set((s) => ({
      selectedIds: s.selectedIds.includes(id)
        ? s.selectedIds.filter((x) => x !== id)
        : [...s.selectedIds, id],
    })),

  selectMany: (ids) => set({ selectedIds: ids }),

  clearSelection: () => set({ selectedIds: [] }),

  addObject: (o) =>
    set((s) => {
      if (!s.canvas) return s;
      return {
        canvas: { ...s.canvas, objects: [...s.canvas.objects, o] },
        selectedIds: [o.id],
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  addObjects: (list) =>
    set((s) => {
      if (!s.canvas || list.length === 0) return s;
      return {
        canvas: { ...s.canvas, objects: [...s.canvas.objects, ...list] },
        selectedIds: list.map((o) => o.id),
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  duplicateSelected: (offset = { dx: 0, dy: 0 }) => {
    // Zustand's `set` callback runs synchronously, so we can capture the
    // generated ids via closure and return them to the caller after `set`.
    let newIds: string[] = [];
    set((s) => {
      if (!s.canvas || s.selectedIds.length === 0) return s;
      const selectedSet = new Set(s.selectedIds);
      const clones: EditorObject[] = [];
      for (const obj of s.canvas.objects) {
        if (!selectedSet.has(obj.id)) continue;
        // Spread preserves the `type` discriminator so TS keeps the union
        // narrow per-object — text stays text, image stays image, etc.
        clones.push({
          ...obj,
          id: newObjectId(),
          x: obj.x + offset.dx,
          y: obj.y + offset.dy,
        } as EditorObject);
      }
      if (clones.length === 0) return s;
      newIds = clones.map((c) => c.id);
      return {
        canvas: { ...s.canvas, objects: [...s.canvas.objects, ...clones] },
        selectedIds: newIds,
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    });
    return newIds;
  },

  updateObject: (id, patch) =>
    set((s) => {
      if (!s.canvas) return s;
      return {
        canvas: {
          ...s.canvas,
          objects: s.canvas.objects.map((o) =>
            o.id === id ? ({ ...o, ...patch } as EditorObject) : o,
          ),
        },
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  deleteObject: (id) =>
    set((s) => {
      if (!s.canvas) return s;
      return {
        canvas: {
          ...s.canvas,
          objects: s.canvas.objects.filter((o) => o.id !== id),
        },
        selectedIds: s.selectedIds.filter((x) => x !== id),
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  alignObjects: (mode) =>
    set((s) => {
      if (!s.canvas || s.selectedIds.length === 0) return s;
      const positions = computeAlignedPositions(
        s.canvas.objects,
        s.selectedIds,
        s.canvas.stage,
        mode,
      );
      if (positions.size === 0) return s;
      return {
        canvas: {
          ...s.canvas,
          objects: s.canvas.objects.map((o) => {
            const p = positions.get(o.id);
            return p ? ({ ...o, x: p.x, y: p.y } as EditorObject) : o;
          }),
        },
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  reorderObjects: (mode) =>
    set((s) => {
      if (!s.canvas || s.selectedIds.length === 0) return s;
      const next = computeReordered(s.canvas.objects, s.selectedIds, mode);
      if (next === s.canvas.objects) return s; // no-op (already at edge)
      return {
        canvas: { ...s.canvas, objects: next },
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

  undo: () =>
    set((s) => {
      if (!s.canvas || s.past.length === 0) return s;
      const [previous, ...rest] = s.past;
      return {
        canvas: previous,
        past: rest,
        future: [s.canvas, ...s.future],
        dirty: true,
        selectedIds: [],
      };
    }),

  redo: () =>
    set((s) => {
      if (!s.canvas || s.future.length === 0) return s;
      const [next, ...rest] = s.future;
      return {
        canvas: next,
        future: rest,
        past: [s.canvas, ...s.past],
        dirty: true,
        selectedIds: [],
      };
    }),
}));

/** Generate a unique id — short enough to read in JSON dumps. */
export function newObjectId(): string {
  return Math.random().toString(36).slice(2, 10);
}
