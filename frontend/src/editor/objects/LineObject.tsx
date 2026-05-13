import type Konva from "konva";
import { Line } from "react-konva";
import type { LineObject as LineObjectModel } from "../types";

type Props = {
  object: LineObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: (e: Konva.KonvaEventObject<unknown>) => void;
  onChange: (patch: Partial<LineObjectModel>) => void;
  onDragStart?: (e: Konva.KonvaEventObject<DragEvent>) => void;
  onDragMoved?: (patch: { x: number; y: number }, e: Konva.KonvaEventObject<DragEvent>) => void;
};

export function LineObject({
  object,
  scale,
  draggable,
  onSelect,
  onChange,
  onDragStart,
  onDragMoved,
}: Props) {
  return (
    <Line
      id={object.id}
      x={object.x * scale}
      y={object.y * scale}
      points={object.points.map((p) => p * scale)}
      stroke={object.stroke}
      strokeWidth={object.strokeWidth * scale}
      lineCap="round"
      rotation={object.rotation ?? 0}
      opacity={object.printable === false ? 0.5 : 1}
      draggable={draggable}
      hitStrokeWidth={Math.max(8, object.strokeWidth * scale * 4)}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragStart={onDragStart}
      onDragEnd={(e) => {
        const patch = { x: e.target.x() / scale, y: e.target.y() / scale };
        if (onDragMoved) onDragMoved(patch, e);
        else onChange(patch);
      }}
      onTransformEnd={(e) => {
        // Points are relative to the line's anchor (x,y). Scale each pair
        // by scaleX/scaleY so the geometry persists; then reset the
        // visual scale on the node.
        const node = e.target as Konva.Line;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        node.scaleX(1);
        node.scaleY(1);
        onChange({
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
          points: object.points.map((p, i) => p * (i % 2 === 0 ? scaleX : scaleY)),
        });
      }}
    />
  );
}
