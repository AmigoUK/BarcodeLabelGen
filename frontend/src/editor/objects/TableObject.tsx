import type Konva from "konva";
import { Group, Line, Rect, Text } from "react-konva";
import type { TableObject as TableObjectModel } from "../types";

const PAD_MM = 0.8;

/** Cumulative column x-offsets in mm (0 … width) — mirrors the backend. */
function tableColEdges(object: TableObjectModel): number[] {
  const { cols, width, colWidths } = object;
  const widths =
    colWidths && colWidths.length === cols && colWidths.every((w) => w > 0)
      ? colWidths
      : Array.from({ length: cols }, () => width / cols);
  const edges = [0];
  for (const w of widths) edges.push(edges[edges.length - 1] + w);
  return edges;
}

type Props = {
  object: TableObjectModel;
  scale: number;
  draggable: boolean;
  onSelect: (e: Konva.KonvaEventObject<unknown>) => void;
  onChange: (patch: Partial<TableObjectModel>) => void;
  onDragStart?: (e: Konva.KonvaEventObject<DragEvent>) => void;
  onDragMoved?: (patch: { x: number; y: number }, e: Konva.KonvaEventObject<DragEvent>) => void;
};

export function TableObject({
  object,
  scale,
  draggable,
  onSelect,
  onChange,
  onDragStart,
  onDragMoved,
}: Props) {
  const edges = tableColEdges(object);
  const rowH = object.height / object.rows;
  const strokeW = (object.strokeWidth ?? 0.2) * scale;

  return (
    <Group
      id={object.id}
      x={object.x * scale}
      y={object.y * scale}
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
        // Fold the transformer's scale into width/height (and colWidths) —
        // same pattern as RectObject.
        const node = e.target as Konva.Group;
        const scaleX = node.scaleX();
        const scaleY = node.scaleY();
        const rotation = node.rotation();
        node.scaleX(1);
        node.scaleY(1);
        onChange({
          x: node.x() / scale,
          y: node.y() / scale,
          rotation,
          width: Math.max(2, object.width * Math.abs(scaleX)),
          height: Math.max(2, object.height * Math.abs(scaleY)),
          colWidths: object.colWidths?.map((w) => Math.max(1, w * Math.abs(scaleX))),
        });
      }}
    >
      {/* Hit area + outer border */}
      <Rect
        x={0}
        y={0}
        width={object.width * scale}
        height={object.height * scale}
        stroke={object.stroke}
        strokeWidth={strokeW}
        fill="transparent"
      />
      {/* Inner grid */}
      {edges.slice(1, -1).map((ex, i) => (
        <Line
          key={`v${i}`}
          points={[ex * scale, 0, ex * scale, object.height * scale]}
          stroke={object.stroke}
          strokeWidth={strokeW}
        />
      ))}
      {Array.from({ length: object.rows - 1 }, (_, i) => (
        <Line
          key={`h${i}`}
          points={[0, (i + 1) * rowH * scale, object.width * scale, (i + 1) * rowH * scale]}
          stroke={object.stroke}
          strokeWidth={strokeW}
        />
      ))}
      {/* Cell texts */}
      {object.cells.slice(0, object.rows).flatMap((row, r) =>
        row.slice(0, object.cols).map((cell, col) =>
          cell ? (
            <Text
              key={`c${r}-${col}`}
              x={(edges[col] + PAD_MM) * scale}
              y={(r * rowH + PAD_MM) * scale}
              width={Math.max(1, edges[col + 1] - edges[col] - 2 * PAD_MM) * scale}
              height={Math.max(1, rowH - 2 * PAD_MM) * scale}
              text={cell}
              fontSize={object.fontSize * scale}
              fontFamily={object.fontFamily}
              fontStyle={object.headerRow && r === 0 ? "bold" : "normal"}
              fill={object.fill}
              wrap="word"
              ellipsis
              listening={false}
            />
          ) : null,
        ),
      )}
    </Group>
  );
}
