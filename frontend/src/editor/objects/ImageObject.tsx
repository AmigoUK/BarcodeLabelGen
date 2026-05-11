import { Image as KonvaImage } from "react-konva";
import useImage from "use-image";
import { assetImageUrl } from "../../hooks/useAssets";
import type { ImageObject as ImageObjectModel } from "../types";

type Props = {
  object: ImageObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: () => void;
  onDragEnd: (xMm: number, yMm: number) => void;
};

export function ImageObject({ object, scale, draggable, onSelect, onDragEnd }: Props) {
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
      draggable={draggable}
      onMouseDown={onSelect}
      onTap={onSelect}
      onDragEnd={(e) => onDragEnd(e.target.x() / scale, e.target.y() / scale)}
    />
  );
}
