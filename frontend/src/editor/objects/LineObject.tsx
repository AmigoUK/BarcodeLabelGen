import type Konva from "konva";
import { Line } from "react-konva";
import type { LineObject as LineObjectModel } from "../types";

type Props = {
  object: LineObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onChange: (patch: Partial<LineObjectModel>) => void;
};

export function LineObject({ object, scale, draggable, onSelect, onChange }: Props) {
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
      draggable={draggable}
      hitStrokeWidth={Math.max(8, object.strokeWidth * scale * 4)}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragEnd={(e) => onChange({ x: e.target.x() / scale, y: e.target.y() / scale })}
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
