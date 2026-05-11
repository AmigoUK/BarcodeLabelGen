import type Konva from "konva";
import { Rect } from "react-konva";
import type { RectObject as RectObjectModel } from "../types";

type Props = {
  object: RectObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onChange: (patch: Partial<RectObjectModel>) => void;
};

export function RectObject({ object, scale, draggable, onSelect, onChange }: Props) {
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
      onDragEnd={(e) => onChange({ x: e.target.x() / scale, y: e.target.y() / scale })}
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
