import type { EditorObject } from "./types";

/**
 * Computes the on-screen scale (px per mm) so the entire stage fits inside
 * the container with a small padding. Returns 0 when the container hasn't
 * been measured yet, so the caller can skip rendering until layout settles
 * — otherwise we'd briefly draw a 100-px-wide stub and then resize.
 */
export function fitScale(
  container: { width: number; height: number },
  stage: { width_mm: number; height_mm: number },
  paddingPx = 16,
): number {
  if (container.width <= 0 || container.height <= 0) return 0;
  const availW = Math.max(50, container.width - paddingPx * 2);
  const availH = Math.max(50, container.height - paddingPx * 2);
  const scaleX = availW / stage.width_mm;
  const scaleY = availH / stage.height_mm;
  return Math.min(scaleX, scaleY);
}

export type BoundsMm = { x: number; y: number; w: number; h: number };

/**
 * Axis-aligned bounding box of an editor object, in millimetres,
 * top-left origin. Rotation is intentionally ignored — alignment
 * targets the unrotated AABB, which matches what Konva's transformer
 * draws around rotated nodes.
 *
 * For single-line text the width depends on font + glyphs; we
 * approximate (`fontSize * 0.55 * len`) rather than touch the Konva
 * node, so the helper stays pure data — easy to test, easy to call
 * from the store.
 */
export function getBoundsMm(obj: EditorObject): BoundsMm {
  switch (obj.type) {
    case "rect":
    case "image":
    case "barcode":
    case "table":
      return { x: obj.x, y: obj.y, w: obj.width, h: obj.height };
    case "text": {
      // Block mode: width AND height set → use them directly.
      if (
        typeof obj.width === "number" &&
        obj.width > 0 &&
        typeof obj.height === "number" &&
        obj.height > 0
      ) {
        return { x: obj.x, y: obj.y, w: obj.width, h: obj.height };
      }
      // Single-line: approximate. A character of width ~0.55 of the
      // font size is a reasonable Helvetica/Inter mean (narrow "i" to
      // wide "M" average around there).
      const lines = obj.text.split("\n");
      const longest = lines.reduce((acc, l) => (l.length > acc ? l.length : acc), 1);
      const w = obj.width ?? Math.max(1, obj.fontSize * 0.55 * longest);
      const h = obj.fontSize * 1.2 * lines.length;
      return { x: obj.x, y: obj.y, w, h };
    }
    case "line": {
      let minX = Infinity;
      let maxX = -Infinity;
      let minY = Infinity;
      let maxY = -Infinity;
      for (let i = 0; i + 1 < obj.points.length; i += 2) {
        const px = obj.points[i];
        const py = obj.points[i + 1];
        if (px < minX) minX = px;
        if (px > maxX) maxX = px;
        if (py < minY) minY = py;
        if (py > maxY) maxY = py;
      }
      // Defend against degenerate (no points) by collapsing to a 0-size
      // box at the anchor.
      if (!isFinite(minX)) {
        return { x: obj.x, y: obj.y, w: 0, h: 0 };
      }
      return {
        x: obj.x + minX,
        y: obj.y + minY,
        w: maxX - minX,
        h: maxY - minY,
      };
    }
  }
}
