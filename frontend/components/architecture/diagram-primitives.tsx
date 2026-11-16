// Shared primitives for the fixed-pixel diagrams on the Architecture page
// (system map, control-plane, token sequence, deployment). Each diagram is a
// `position:relative` canvas of an exact width/height, and these two pieces
// are absolutely positioned inside it exactly as the design prototype lays
// them out — a straight transcription of coordinates rather than a generic
// auto-router, to keep the result pixel-faithful.

export interface SegProps {
  x: number;
  y: number;
  w: number;
  h: number;
  d: string;
  color: string;
  markerId: string;
  arrow?: boolean;
  hidden?: boolean;
  dash?: boolean;
  label?: string;
}

/** One straight line segment, with an optional arrowhead marker. */
export function Seg({ x, y, w, h, d, color, markerId, arrow, hidden, dash, label }: SegProps) {
  return (
    <svg
      role={hidden ? undefined : "img"}
      aria-hidden={hidden ? true : undefined}
      aria-label={hidden ? undefined : label}
      width={w}
      height={h}
      viewBox={`0 0 ${w} ${h}`}
      preserveAspectRatio="none"
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        overflow: "visible",
        fill: "none",
        stroke: color,
        strokeWidth: 1.5,
        strokeDasharray: dash ? "5 5" : undefined,
        strokeLinecap: "round",
        strokeLinejoin: "round",
      }}
    >
      {arrow && (
        <defs>
          <marker id={markerId} orient="auto" markerWidth={5} markerHeight={5} refX={2} refY={2} overflow="visible">
            <path d="M0 0 L4 2 L0 4 Z" fill={color} stroke="none" />
          </marker>
        </defs>
      )}
      <path d={d} markerEnd={arrow ? `url(#${markerId})` : undefined} />
    </svg>
  );
}

export interface BoxProps {
  x: number;
  y: number;
  w: number;
  h: number;
  title: string;
  sub?: string;
  border: string;
  bg?: string;
  fontSize?: number;
}

/** One absolutely positioned labelled box ("Orchestrator", "Actor LLM", …). */
export function Box({ x, y, w, h, title, sub, border, bg = "#101114", fontSize = 14 }: BoxProps) {
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        height: h,
        boxSizing: "border-box",
        padding: "8px 10px",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
        textAlign: "center",
        background: bg,
        border: `1px solid ${border}`,
        borderRadius: "6px",
        color: "rgba(255,255,255,0.95)",
        fontSize,
        lineHeight: 1.3,
      }}
    >
      <span>
        {sub ? <b style={{ fontWeight: 500 }}>{title}</b> : title}
        {sub && (
          <>
            <br />
            <span style={{ fontSize: fontSize - 1.5, color: "rgba(255,255,255,0.62)" }}>{sub}</span>
          </>
        )}
      </span>
    </div>
  );
}

export interface CaptionProps {
  x: number;
  y: number;
  w: number;
  color: string;
  align?: "left" | "center";
  text: string;
}

/** A small floating text caption positioned on a diagram canvas. */
export function Caption({ x, y, w, color, align = "center", text }: CaptionProps) {
  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: w,
        textAlign: align,
        fontSize: 13,
        lineHeight: "16px",
        color,
      }}
    >
      {text}
    </div>
  );
}
