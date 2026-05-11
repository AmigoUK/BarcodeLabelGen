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

export type EditorObject = TextObject | RectObject | LineObject | ImageObject;

export type CanvasData = {
  version: 1;
  stage: { width_mm: number; height_mm: number };
  objects: EditorObject[];
};

export const emptyCanvas = (widthMm: number, heightMm: number): CanvasData => ({
  version: 1,
  stage: { width_mm: widthMm, height_mm: heightMm },
  objects: [],
});
