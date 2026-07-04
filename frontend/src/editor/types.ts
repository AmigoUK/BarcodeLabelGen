/**
 * Editor object types — coordinates and sizes are in MILLIMETRES.
 * The Canvas component scales to pixels at render time. The full tree is
 * what gets serialized to the backend's `canvas_data` JSONB column.
 */

export type EditorObjectBase = {
  id: string;
  /** mm from stage origin */
  x: number;
  y: number;
  rotation?: number;
  /** When true, the object can be selected (so it can be unlocked from
   *  the right panel) but not dragged or transformed on the canvas.
   *  Used by the background-reference workflow. Defaults to false. */
  locked?: boolean;
  /** When false, the renderer skips this object in PDF output (both
   *  single-label sync and batch). Defaults to true (omitted = printable).
   *  Used by reference images that should only appear in the editor. */
  printable?: boolean;
  /** Round-trip hints preserved when a label is imported from ZPL (exact
   *  font token, barcode command, field-block params, hex-escape, ^FO
   *  justification). Opaque to the editor and PDF renderer; consumed only
   *  by the backend ZPL generator so re-export stays faithful. */
  zpl?: Record<string, unknown>;
};

export type TextObject = EditorObjectBase & {
  type: "text";
  text: string;
  /** mm */
  fontSize: number;
  fontFamily: string;
  fill: string;
  fontStyle?: "normal" | "italic";
  fontWeight?: "normal" | "bold";
  align?: "left" | "center" | "right";
  width?: number; // mm — wraps at this width
  // --- Text-block extensions (active when both width AND height are set) ---
  height?: number; // mm — wrap-box height
  autoFit?: boolean; // shrink fontSize to fit, between min/max
  minFontSize?: number; // mm
  maxFontSize?: number; // mm
};

export type RectObject = EditorObjectBase & {
  type: "rect";
  width: number; // mm
  height: number; // mm
  fill: string;
  stroke?: string;
  strokeWidth?: number; // mm
};

export type LineObject = EditorObjectBase & {
  type: "line";
  /** absolute mm pairs [x1, y1, x2, y2, …] */
  points: number[];
  stroke: string;
  strokeWidth: number; // mm
};

export type ImageObject = EditorObjectBase & {
  type: "image";
  width: number; // mm
  height: number; // mm
  /** Backend asset id; image src is /api/assets/images/:assetId */
  assetId: number;
};

export type BarcodeType = "ean13" | "ean14" | "gtin" | "code128" | "gs1_128" | "qr";

export type BarcodeObject = EditorObjectBase & {
  type: "barcode";
  barcodeType: BarcodeType;
  data: string;
  width: number; // mm
  height: number; // mm
};

export type TableObject = EditorObjectBase & {
  type: "table";
  width: number; // mm — total (equals sum(colWidths) when present)
  height: number; // mm — total; rows split it equally
  rows: number;
  cols: number;
  /** rows × cols cell texts; {{placeholders}} and {{date+x}} allowed */
  cells: string[][];
  /** mm per column; omitted/invalid → equal split of width */
  colWidths?: number[];
  /** bold first row */
  headerRow?: boolean;
  fontSize: number; // mm
  fontFamily: string;
  fill: string; // text colour
  stroke: string; // grid colour
  strokeWidth: number; // mm
};

export type EditorObject =
  | TextObject
  | RectObject
  | LineObject
  | ImageObject
  | BarcodeObject
  | TableObject;

export type CanvasData = {
  version: 1;
  stage: { width_mm: number; height_mm: number; zpl?: Record<string, unknown> };
  objects: EditorObject[];
};

export const emptyCanvas = (widthMm: number, heightMm: number): CanvasData => ({
  version: 1,
  stage: { width_mm: widthMm, height_mm: heightMm },
  objects: [],
});
