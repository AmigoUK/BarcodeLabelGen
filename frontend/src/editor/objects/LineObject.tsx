import { Line } from "react-konva";
import type { LineObject as LineObjectModel } from "../types";

type Props = {
  object: LineObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onDragEnd: (xMm: number, yMm: number) => void;
};

export function LineObject({ object, scale, draggable, onSelect, onDragEnd }: Props) {
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
      onDragEnd={(e) => onDragEnd(e.target.x() / scale, e.target.y() / scale)}
    />
  );
}
