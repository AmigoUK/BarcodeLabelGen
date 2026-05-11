import type Konva from "konva";
import { Text } from "react-konva";
import type { TextObject as TextObjectModel } from "../types";

type Props = {
  object: TextObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onChange: (patch: Partial<TextObjectModel>) => void;
};

export function TextObject({ object, scale, draggable, onSelect, onChange }: Props) {
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
      onDragEnd={(e) => onChange({ x: e.target.x() / scale, y: e.target.y() / scale })}
      onTransformEnd={(e) => {
        // Konva's Transformer applies scaleX/scaleY to the node. If we
        // don't fold that scale back into fontSize/width and reset the
        // transform, the visual change is lost on the next render (and
        // on reload from the store).
        const node = e.target as Konva.Text;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        const fontScale = (Math.abs(scaleX) + Math.abs(scaleY)) / 2;
        node.scaleX(1);
        node.scaleY(1);
        const patch: Partial<TextObjectModel> = {
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
          fontSize: Math.max(0.5, object.fontSize * fontScale),
        };
        if (object.width !== undefined) {
          patch.width = Math.max(1, object.width * Math.abs(scaleX));
        }
        onChange(patch);
      }}
    />
  );
}
