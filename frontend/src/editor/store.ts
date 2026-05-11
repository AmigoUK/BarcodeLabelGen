/**
 * Zustand store for the editor — single source of truth for the canvas
 * being edited. Keeps the `dirty` flag updated so autosave / save buttons
 * can react. Save/load round-trips happen through hooks (TanStack Query),
 * which call into here via `setCanvas`.
 */

import { create } from "zustand";
import type { CanvasData, EditorObject } from "./types";

type State = {
  canvas: CanvasData | null;
  /** id of currently selected object, or null */
  selectedId: string | null;
  /** true when the canvas differs from what the server last saw */
  dirty: boolean;

  // --- mutations ---
  setCanvas: (c: CanvasData) => void;
  markClean: () => void;
  select: (id: string | null) => void;

  addObject: (o: EditorObject) => void;
  updateObject: (id: string, patch: Partial<EditorObject>) => void;
  deleteObject: (id: string) => void;
};

export const useEditorStore = create<State>((set) => ({
  canvas: null,
  selectedId: null,
  dirty: false,

  setCanvas: (c) =>
    set({
      canvas: c,
      selectedId: null,
      dirty: false,
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
      };
    }),
}));

/** Generate a unique id — short enough to read in JSON dumps. */
export function newObjectId(): string {
  return Math.random().toString(36).slice(2, 10);
}
