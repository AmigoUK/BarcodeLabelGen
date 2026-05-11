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

const HISTORY_LIMIT = 50;

type State = {
  canvas: CanvasData | null;
  /** id of currently selected object, or null */
  selectedId: string | null;
  /** true when the canvas differs from what the server last saw */
  dirty: boolean;
  /** previous canvas snapshots (most recent first), capped at HISTORY_LIMIT */
  past: CanvasData[];
  future: CanvasData[];

  // --- mutations ---
  setCanvas: (c: CanvasData) => void;
  markClean: () => void;
  select: (id: string | null) => void;

  addObject: (o: EditorObject) => void;
  updateObject: (id: string, patch: Partial<EditorObject>) => void;
  deleteObject: (id: string) => void;

  undo: () => void;
  redo: () => void;
};

const pushHistory = (past: CanvasData[], snapshot: CanvasData): CanvasData[] => {
  const next = [snapshot, ...past];
  return next.length > HISTORY_LIMIT ? next.slice(0, HISTORY_LIMIT) : next;
};

export const useEditorStore = create<State>((set) => ({
  canvas: null,
  selectedId: null,
  dirty: false,
  past: [],
  future: [],

  setCanvas: (c) =>
    set({
      canvas: c,
      selectedId: null,
      dirty: false,
      past: [],
      future: [],
    }),

  markClean: () => set({ dirty: false }),

  select: (id) => set({ selectedId: id }),

  addObject: (o) =>
    set((s) => {
      if (!s.canvas) return s;
      return {
        canvas: { ...s.canvas, objects: [...s.canvas.objects, o] },
        selectedId: o.id,
        dirty: true,
        past: pushHistory(s.past, s.canvas),
        future: [],
      };
    }),

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
        selectedId: s.selectedId === id ? null : s.selectedId,
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
        selectedId: null,
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
        selectedId: null,
      };
    }),
}));

/** Generate a unique id — short enough to read in JSON dumps. */
export function newObjectId(): string {
  return Math.random().toString(36).slice(2, 10);
}
