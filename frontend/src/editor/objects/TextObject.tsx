import { Text } from "react-konva";
import type { TextObject as TextObjectModel } from "../types";

type Props = {
  object: TextObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onDragEnd: (xMm: number, yMm: number) => void;
};

export function TextObject({ object, scale, draggable, onSelect, onDragEnd }: Props) {
  return (
    <Text
      id={object.id}
      x={object.x * scale}
      y={object.y * scale}
      text={object.text}
      fontSize={object.fontSize * scale}
      fontFamily={object.fontFamily}
      fill={object.fill}
      fontStyle={
        object.fontWeight === "bold" && object.fontStyle === "italic"
          ? "italic bold"
          : (object.fontWeight ?? object.fontStyle ?? "normal")
      }
      align={object.align ?? "left"}
      width={object.width ? object.width * scale : undefined}
      rotation={object.rotation ?? 0}
      draggable={draggable}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragEnd={(e) => onDragEnd(e.target.x() / scale, e.target.y() / scale)}
    />
  );
}
