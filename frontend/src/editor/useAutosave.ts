/**
 * Debounced autosave: waits `delayMs` after the last canvas change,
 * then calls `save(canvas)`. Cancels in-flight timer on unmount or when
 * the canvas reference changes again before the delay elapses.
 *
 * Returns the wall-clock time of the last successful autosave (or null).
 */

import { useEffect, useState } from "react";
import type { CanvasData } from "./types";

type Status = "idle" | "saving" | "saved" | "error";

export function useAutosave(
  canvas: CanvasData | null,
  dirty: boolean,
  save: (c: CanvasData) => Promise<void>,
  delayMs = 30_000,
): { status: Status; lastSavedAt: Date | null; error: string | null } {
  const [status, setStatus] = useState<Status>("idle");
  const [lastSavedAt, setLastSavedAt] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!canvas || !dirty) return;

    const timer = window.setTimeout(async () => {
      setStatus("saving");
      try {
        await save(canvas);
        setStatus("saved");
        setLastSavedAt(new Date());
        setError(null);
      } catch (err) {
        setStatus("error");
        setError(err instanceof Error ? err.message : String(err));
      }
    }, delayMs);

    return () => window.clearTimeout(timer);
  }, [canvas, dirty, save, delayMs]);

  return { status, lastSavedAt, error };
}
