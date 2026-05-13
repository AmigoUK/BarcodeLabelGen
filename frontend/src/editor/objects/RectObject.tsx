import type Konva from "konva";
import { Rect } from "react-konva";
import type { RectObject as RectObjectModel } from "../types";

type Props = {
  object: RectObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: (e: Konva.KonvaEventObject<unknown>) => void;
  onChange: (patch: Partial<RectObjectModel>) => void;
  onDragStart?: (e: Konva.KonvaEventObject<DragEvent>) => void;
  onDragMoved?: (patch: { x: number; y: number }, e: Konva.KonvaEventObject<DragEvent>) => void;
};

export function RectObject({
  object,
  scale,
  draggable,
  onSelect,
  onChange,
  onDragStart,
  onDragMoved,
}: Props) {
  return (
    <Rect
      id={object.id}
      x={object.x * scale}
      y={object.y * scale}
      width={object.width * scale}
      height={object.height * scale}
      fill={object.fill}
      stroke={object.stroke}
      strokeWidth={(object.strokeWidth ?? 0) * scale}
      rotation={object.rotation ?? 0}
      opacity={object.printable === false ? 0.5 : 1}
      draggable={draggable}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragStart={onDragStart}
      onDragEnd={(e) => {
        const patch = { x: e.target.x() / scale, y: e.target.y() / scale };
        if (onDragMoved) onDragMoved(patch, e);
        else onChange(patch);
      }}
      onTransformEnd={(e) => {
        // Fold the transformer's scaleX/scaleY back into width/height so
        // the resize survives reload, then reset the visual scale.
        const node = e.target as Konva.Rect;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        node.scaleX(1);
        node.scaleY(1);
        onChange({
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
          width: Math.max(0.5, object.width * Math.abs(scaleX)),
          height: Math.max(0.5, object.height * Math.abs(scaleY)),
        });
      }}
    />
  );
}
