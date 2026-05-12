import type Konva from "konva";
import { Image as KonvaImage, Rect, Text } from "react-konva";
import useImage from "use-image";
import type { BarcodeObject as BarcodeObjectModel } from "../types";

type Props = {
  object: BarcodeObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: (e: Konva.KonvaEventObject<unknown>) => void;
  onChange: (patch: Partial<BarcodeObjectModel>) => void;
};

/** The URL the backend serves the rendered PNG from.
 * Same input → same image (and the backend sets Cache-Control), so the
 * browser keeps it cached as long as the user is on this template. */
function barcodePreviewUrl(o: BarcodeObjectModel): string {
  const params = new URLSearchParams({
    type: o.barcodeType,
    data: o.data,
    width_mm: String(o.width),
    height_mm: String(o.height),
  });
  return `/api/barcodes/preview?${params.toString()}`;
}

export function BarcodeObject({ object, scale, draggable, onSelect, onChange }: Props) {
  // useImage transitions through "loading" → "loaded" / "failed". On
  // failure (e.g. invalid data) we show a clearly-broken placeholder
  // box so the user sees that something's wrong without the canvas
  // becoming a confusing void.
  const [img, status] = useImage(barcodePreviewUrl(object), "anonymous");

  const onTransformEnd = (e: Konva.KonvaEventObject<Event>) => {
    const node = e.target;
    const scaleX = node.scaleX();
    const scaleY = node.scaleY();
    const rotation = node.rotation();
    node.scaleX(1);
    node.scaleY(1);
    onChange({
      x: node.x() / scale,
      y: node.y() / scale,
      rotation,
      width: Math.max(5, object.width * Math.abs(scaleX)),
      height: Math.max(5, object.height * Math.abs(scaleY)),
    });
  };

  const commonProps = {
    id: object.id,
    x: object.x * scale,
    y: object.y * scale,
    width: object.width * scale,
    height: object.height * scale,
    rotation: object.rotation ?? 0,
    opacity: object.printable === false ? 0.5 : 1,
    draggable,
    onMouseDown: onSelect,
    onTap: onSelect,
    onDragEnd: (e: Konva.KonvaEventObject<DragEvent>) =>
      onChange({ x: e.target.x() / scale, y: e.target.y() / scale }),
    onTransformEnd,
  };

  if (status === "loaded" && img) {
    return <KonvaImage {...commonProps} image={img} />;
  }

  // Placeholder for empty/invalid data: dashed outline + label
  return (
    <>
      <Rect
        {...commonProps}
        fill="#f1f5f9"
        stroke={status === "failed" ? "#e11d48" : "#94a3b8"}
        strokeWidth={1}
        dash={[6, 4]}
      />
      <Text
        x={object.x * scale}
        y={object.y * scale + (object.height * scale) / 2 - 8}
        width={object.width * scale}
        text={status === "failed" ? "⚠ invalid data" : object.barcodeType}
        align="center"
        fontSize={Math.min(14, object.height * scale * 0.3)}
        fill={status === "failed" ? "#e11d48" : "#64748b"}
        listening={false}
      />
    </>
  );
}
