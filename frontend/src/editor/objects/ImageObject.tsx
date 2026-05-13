import type Konva from "konva";
import { Image as KonvaImage } from "react-konva";
import useImage from "use-image";
import { assetImageUrl } from "../../hooks/useAssets";
import type { ImageObject as ImageObjectModel } from "../types";

type Props = {
  object: ImageObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: (e: Konva.KonvaEventObject<unknown>) => void;
  onChange: (patch: Partial<ImageObjectModel>) => void;
  onDragStart?: (e: Konva.KonvaEventObject<DragEvent>) => void;
  onDragMoved?: (patch: { x: number; y: number }, e: Konva.KonvaEventObject<DragEvent>) => void;
};

export function ImageObject({
  object,
  scale,
  draggable,
  onSelect,
  onChange,
  onDragStart,
  onDragMoved,
}: Props) {
  const [img] = useImage(assetImageUrl(object.assetId), "anonymous");
  return (
    <KonvaImage
      id={object.id}
      x={object.x * scale}
      y={object.y * scale}
      width={object.width * scale}
      height={object.height * scale}
      image={img}
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
        const node = e.target as Konva.Image;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        node.scaleX(1);
        node.scaleY(1);
        onChange({
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
          width: Math.max(1, object.width * Math.abs(scaleX)),
          height: Math.max(1, object.height * Math.abs(scaleY)),
        });
      }}
    />
  );
}
