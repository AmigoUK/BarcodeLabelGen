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
  // "Block mode": both width and height set → Konva wraps text inside the
  // box. Without height the element behaves like the legacy single-line
  // text object.
  const hasWidth = typeof object.width === "number" && object.width > 0;
  const hasHeight = typeof object.height === "number" && object.height > 0;
  const isBlock = hasWidth && hasHeight;

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
      width={hasWidth ? object.width! * scale : undefined}
      height={isBlock ? object.height! * scale : undefined}
      wrap={hasWidth ? "word" : "none"}
      rotation={object.rotation ?? 0}
      draggable={draggable}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragEnd={(e) => onChange({ x: e.target.x() / scale, y: e.target.y() / scale })}
      onTransformEnd={(e) => {
        // Konva's Transformer applies scaleX/scaleY to the node. Fold it
        // back into fontSize / width / height so the change persists.
        const node = e.target as Konva.Text;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        node.scaleX(1);
        node.scaleY(1);
        const patch: Partial<TextObjectModel> = {
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
        };
        if (isBlock) {
          // In block mode the user resizes the BOX, not the font. Keep
          // fontSize stable; resize width/height per scale axis.
          patch.width = Math.max(1, object.width! * Math.abs(scaleX));
          patch.height = Math.max(1, object.height! * Math.abs(scaleY));
        } else {
          // Legacy single-line: scale rescales the font.
          const fontScale = (Math.abs(scaleX) + Math.abs(scaleY)) / 2;
          patch.fontSize = Math.max(0.5, object.fontSize * fontScale);
          if (hasWidth) {
            patch.width = Math.max(1, object.width! * Math.abs(scaleX));
          }
        }
        onChange(patch);
      }}
    />
  );
}
