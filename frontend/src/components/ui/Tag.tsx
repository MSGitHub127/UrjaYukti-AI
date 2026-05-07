import { COLORS } from "@/lib/mapLayers";

interface TagProps {
  text: string;
  color?: string;
  dot?: boolean;
}

export function Tag({ text, color = COLORS.primary, dot = false }: TagProps) {
  return (
    <span
      className="tag"
      style={{ background: color + "18", color, border: `1px solid ${color}33` }}
    >
      {dot && (
        <span
          style={{
            width: 5,
            height: 5,
            borderRadius: "50%",
            background: color,
            display: "inline-block",
          }}
        />
      )}
      {text}
    </span>
  );
}
