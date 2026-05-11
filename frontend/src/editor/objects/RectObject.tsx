import { Rect } from "react-konva";
import type { RectObject as RectObjectModel } from "../types";

type Props = {
  object: RectObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onDragEnd: (xMm: number, yMm: number) => void;
};

export function RectObject({ object, scale, draggable, onSelect, onDragEnd }: Props) {
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
      draggable={draggable}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragEnd={(e) => onDragEnd(e.target.x() / scale, e.target.y() / scale)}
    />
  );
}
