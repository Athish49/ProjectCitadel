import {
  CONTROL_W, CONTROL_H, CONTROL_BOXES, CONTROL_SEGS, CONTROL_CAPTIONS, CONTROL_STATS,
} from "@/lib/data/architecture";
import { Seg, Box, Caption } from "@/components/architecture/diagram-primitives";

export function ControlPlaneDiagram() {
  return (
    <div className="panel" style={{ marginTop: 0 }}>
      <div style={{ overflowX: "auto", padding: "28px 22px" }}>
        <div style={{ position: "relative", width: CONTROL_W, height: CONTROL_H, margin: "0 auto" }}>
          {CONTROL_SEGS.map((s, i) => (
            <Seg
              key={i}
              x={s.x} y={s.y} w={s.w} h={s.h} d={s.d}
              color={s.color} arrow={s.arrow} hidden={s.hidden} label={s.label}
              markerId={`arch-ctrl-ah-${i}`}
            />
          ))}
          {CONTROL_BOXES.map((b) => (
            <Box key={b.title} x={b.x} y={b.y} w={b.w} h={b.h} title={b.title} sub={b.sub} border={b.border} />
          ))}
          {CONTROL_CAPTIONS.map((c) => (
            <Caption key={c.text} x={c.x} y={c.y} w={c.w} color={c.color} align={c.align} text={c.text} />
          ))}
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit,minmax(min(220px,100%),1fr))",
          gap: "1px", background: "rgba(255,255,255,0.08)", borderTop: "1px solid rgba(255,255,255,0.08)",
        }}
      >
        {CONTROL_STATS.map((s) => (
          <div key={s.label} className="cell" style={{ background: "#0c0d0f", padding: "18px 20px" }}>
            <div className="mono" style={{ fontSize: 24, fontWeight: 500 }}>{s.value}</div>
            <div style={{ marginTop: 6, fontSize: 13, color: "rgba(255,255,255,0.62)" }}>{s.label}</div>
          </div>
        ))}
      </div>
    </div>
  );
}
