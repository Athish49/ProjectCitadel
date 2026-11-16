"use client";

import { Fragment, useState } from "react";
import {
  MECHANISM_TABS,
  TOKEN_SEQ_W, TOKEN_SEQ_H, TOKEN_SEQ_BOXES, TOKEN_SEQ_SEGS, TOKEN_SEQ_CAPTIONS, TOKEN_CHECKS,
  DATA_LABELS, OUTPUT_CHECKS,
  SANDBOX_STEPS, SANDBOX_CONTAINER_TAGS, SANDBOX_STEPS_AFTER, SANDBOX_CATEGORIES,
  AUDIT_CHAIN_ROWS,
  DEPLOY_W, DEPLOY_H, DEPLOY_HIGHLIGHT, DEPLOY_BOXES, DEPLOY_SEGS, DEPLOY_CAPTIONS, DEPLOY_NETWORK_NOTE,
} from "@/lib/data/architecture";
import { Seg, Box, Caption } from "@/components/architecture/diagram-primitives";
import styles from "@/components/architecture/architecture.module.css";

const TAB_HEADS: { h3: string; p: string }[] = [
  { h3: "Authority is issued per call, not per agent.", p: "An actor holds no standing permissions. Each tool call needs a fresh signed token that names one tool and one scope, and works once." },
  { h3: "Every value carries a label.", p: "Labels decide which data may enter a model and which may leave the system. Anything from outside also carries an untrusted flag." },
  { h3: "Files are opened where they can do no harm.", p: "Every PDF and image gets its own disposable container. Only plain text and clean pixels come back out." },
  { h3: "Tamper with one row and the chain breaks.", p: "Each audit row stores the hash of the row before it. Database roles can insert but never update or delete." },
  { h3: "One API, two hard network boundaries.", p: "File sandboxes have no network at all. The red-team agent runs on its own network and cannot reach the database." },
];

function ChevronRight() {
  return (
    <svg aria-hidden="true" width="16" height="16" viewBox="0 0 16 16" style={{ flex: "0 0 16px", alignSelf: "center", fill: "none", stroke: "rgba(255,255,255,0.4)", strokeWidth: 1.5, strokeLinecap: "round", strokeLinejoin: "round" }}>
      <path d="M6 3l5 5-5 5" />
    </svg>
  );
}

function SandboxCard({ title, sub }: { title: string; sub: string }) {
  return (
    <div style={{ flex: "1 1 150px", minWidth: 0, border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", background: "#101114", padding: "16px", display: "flex", flexDirection: "column", justifyContent: "center" }}>
      <div style={{ fontSize: 15, fontWeight: 500 }}>{title}</div>
      <div style={{ marginTop: 4, fontSize: 13, color: "rgba(255,255,255,0.62)" }}>{sub}</div>
    </div>
  );
}

export function Mechanisms() {
  const [tab, setTab] = useState(0);
  const [tampered, setTampered] = useState(false);
  const head = TAB_HEADS[tab];

  return (
    <div style={{ marginTop: 44 }}>
      <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
        {MECHANISM_TABS.map((name, i) => {
          const on = i === tab;
          return (
            <button
              key={name}
              type="button"
              className={`pick ${styles.pick}`}
              aria-pressed={on}
              onClick={() => setTab(i)}
              style={{
                fontSize: 14, padding: "8px 16px", minHeight: 44,
                background: on ? "#f4f4f5" : "#0a0b0c",
                borderColor: on ? "#f4f4f5" : "rgba(255,255,255,0.12)",
                color: on ? "#0a0b0c" : "rgba(255,255,255,0.95)",
              }}
            >
              {name}
            </button>
          );
        })}
      </div>

      <div key={tab} className={styles.fadeUp} style={{ marginTop: 28 }}>
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px 40px", alignItems: "baseline", marginBottom: 22 }}>
          <h3 style={{ margin: 0, fontSize: 22, fontWeight: 600, letterSpacing: "-0.02em", flex: "0 1 auto" }}>{head.h3}</h3>
          <p style={{ margin: 0, fontSize: 15, color: "rgba(255,255,255,0.7)", flex: "1 1 380px", maxWidth: 640 }}>{head.p}</p>
        </div>

        {/* ── Tab 0: Capability tokens ── */}
        {tab === 0 && (
          <div className="panel" style={{ marginTop: 0 }}>
            <div style={{ overflowX: "auto", padding: "28px 22px" }}>
              <div style={{ position: "relative", width: TOKEN_SEQ_W, height: TOKEN_SEQ_H, margin: "0 auto" }}>
                {TOKEN_SEQ_SEGS.map((s, i) => (
                  <Seg key={i} x={s.x} y={s.y} w={s.w} h={s.h} d={s.d} color={s.color} arrow={s.arrow} hidden={s.hidden} dash={s.dash} label={s.label} markerId={`arch-tok-ah-${i}`} />
                ))}
                {TOKEN_SEQ_BOXES.map((b) => (
                  <Box key={b.title} x={b.x} y={b.y} w={b.w} h={b.h} title={b.title} sub={b.sub} border={b.border} />
                ))}
                {TOKEN_SEQ_CAPTIONS.map((c) => (
                  <Caption key={c.text} x={c.x} y={c.y} w={c.w} color={c.color} align={c.align} text={c.text} />
                ))}
              </div>
            </div>
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(180px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,0.08)", borderTop: "1px solid rgba(255,255,255,0.08)" }}>
              {TOKEN_CHECKS.map((c) => (
                <div key={c.n} className="cell" style={{ background: "#0c0d0f", padding: "16px 18px" }}>
                  <div className="mono" style={{ fontSize: 11, color: "#3ecf8e" }}>CHECK {c.n}</div>
                  <div style={{ marginTop: 6, fontSize: 15, fontWeight: 500 }}>{c.name}</div>
                  <div style={{ marginTop: 2, fontSize: 13, color: "rgba(255,255,255,0.62)" }}>{c.what}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Tab 1: Data labels ── */}
        {tab === 1 && (
          <>
            <div className="panel" style={{ marginTop: 0, overflowX: "auto" }}>
              <table className={styles.table}>
                <thead>
                  <tr>
                    {["Level", "Example", "May enter a model", "May leave the system"].map((h) => (
                      <th key={h} scope="col" className="mono" style={{ textAlign: "left", padding: "13px 18px", fontSize: 11, fontWeight: 400, letterSpacing: "0.1em", textTransform: "uppercase", color: "rgba(255,255,255,0.58)", borderBottom: "1px solid rgba(255,255,255,0.1)" }}>
                        {h}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {DATA_LABELS.map((row) => (
                    <tr key={row.level}>
                      <td style={{ padding: "15px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 14, verticalAlign: "top" }}>
                        <div className="mono" style={{ fontSize: 12, letterSpacing: "0.08em", color: "rgba(255,255,255,0.9)" }}>{row.level}</div>
                        <div style={{ marginTop: 8, height: 6, width: 160, background: "rgba(255,255,255,0.06)", borderRadius: "2px" }}>
                          <div style={{ height: "100%", width: `${row.bar}%`, background: "rgba(255,255,255,0.9)", borderRadius: "2px" }} />
                        </div>
                      </td>
                      <td style={{ padding: "15px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 14, verticalAlign: "top", color: "rgba(255,255,255,0.85)" }}>{row.example}</td>
                      <td style={{ padding: "15px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 14, verticalAlign: "top", color: "rgba(255,255,255,0.85)" }}>{row.mayEnter}</td>
                      <td style={{ padding: "15px 18px", borderBottom: "1px solid rgba(255,255,255,0.06)", fontSize: 14, verticalAlign: "top", color: "rgba(255,255,255,0.85)" }}>{row.mayLeave}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            <div style={{ marginTop: 40 }}>
              <div className="eb" style={{ fontSize: 11, color: "rgba(255,255,255,0.58)" }}>Output checks, in order</div>
              <div style={{ marginTop: 16, display: "flex", flexWrap: "wrap", gap: "12px" }}>
                {OUTPUT_CHECKS.map((c, i) => (
                  <Fragment key={c.n}>
                    {i > 0 && <ChevronRight />}
                    <div style={{ flex: "1 1 200px", minWidth: 0, border: "1px solid rgba(255,255,255,0.12)", borderRadius: "6px", background: "#101114", padding: "16px 16px 18px" }}>
                      <div className="mono" style={{ fontSize: 12, color: "rgba(255,255,255,0.62)" }}>{c.n}</div>
                      <div style={{ marginTop: 6, fontSize: 15, fontWeight: 500 }}>{c.name}</div>
                      <div style={{ marginTop: 4, fontSize: 13, color: "rgba(255,255,255,0.62)" }}>{c.trigger}</div>
                      <div className="mono" style={{ marginTop: 12, fontSize: 11.5, color: "rgba(255,255,255,0.85)" }}>{c.action}</div>
                    </div>
                  </Fragment>
                ))}
              </div>
            </div>
          </>
        )}

        {/* ── Tab 2: File sandbox ── */}
        {tab === 2 && (
          <div className="panel" style={{ marginTop: 0, padding: "24px 22px" }}>
            <div style={{ display: "flex", flexWrap: "wrap", gap: "12px" }}>
              {SANDBOX_STEPS.map((s, i) => (
                <Fragment key={s.title}>
                  {i > 0 && <ChevronRight />}
                  <SandboxCard title={s.title} sub={s.sub} />
                </Fragment>
              ))}
              <ChevronRight />
              <div style={{ flex: "3 1 380px", minWidth: 0, border: "1px dashed rgba(255,255,255,0.32)", borderRadius: "6px", padding: "16px" }}>
                <div className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", color: "rgba(255,255,255,0.7)" }}>DISPOSABLE CONTAINER</div>
                <div style={{ marginTop: 6, fontSize: 15, fontWeight: 500 }}>Parse, extract, re-encode</div>
                <div style={{ marginTop: 12, display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {SANDBOX_CONTAINER_TAGS.map((tg) => (
                    <span key={tg} className="mono" style={{ fontSize: 11.5, padding: "5px 9px", border: "1px solid rgba(255,255,255,0.14)", borderRadius: "4px", color: "rgba(255,255,255,0.82)" }}>{tg}</span>
                  ))}
                </div>
              </div>
              {SANDBOX_STEPS_AFTER.map((s) => (
                <Fragment key={s.title}>
                  <ChevronRight />
                  <SandboxCard title={s.title} sub={s.sub} />
                </Fragment>
              ))}
            </div>

            <div style={{ marginTop: 24, display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(min(320px,100%),1fr))", gap: "1px", background: "rgba(255,255,255,0.08)", border: "1px solid rgba(255,255,255,0.08)" }}>
              {SANDBOX_CATEGORIES.map((c) => (
                <div key={c.label} className="cell" style={{ padding: "18px 20px" }}>
                  <div className="mono" style={{ fontSize: 11, letterSpacing: "0.1em", color: c.color }}>{c.label}</div>
                  <div style={{ marginTop: 8, fontSize: 14.5, color: "rgba(255,255,255,0.85)" }}>{c.text}</div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ── Tab 3: Audit chain ── */}
        {tab === 3 && (
          <div className="panel" style={{ marginTop: 0 }}>
            <div className="ph">
              <span className="eb" style={{ fontSize: 11 }}>{"Four consecutive rows · illustrative hashes"}</span>
              <button type="button" className="btn btn-g" onClick={() => setTampered((t) => !t)} style={{ minHeight: 40, padding: "0 14px", fontSize: 13.5 }}>
                {tampered ? "Restore row 42" : "Tamper with row 42"}
              </button>
            </div>
            <div style={{ padding: "24px 22px", display: "flex", flexWrap: "wrap", gap: "12px" }}>
              {AUDIT_CHAIN_ROWS.map((row, i) => {
                const bad = tampered && i >= 1;
                const src = tampered && i === 1;
                const mism = tampered && i === 2;
                const unverifiable = tampered && i === 3;
                const event = i === 1 ? (tampered ? row.eventTampered : row.eventOk) : row.eventOk;
                const hash = i === 1 ? (tampered ? row.hashTampered : row.hashOk) : row.hashOk;
                const status = src ? "EDITED" : mism ? "PREV MISMATCH" : unverifiable ? "UNVERIFIABLE" : "VERIFIED";
                const sfg = src || mism ? "#f0787c" : unverifiable ? "#e2a336" : "#3ecf8e";
                const bd = bad && i <= 2 ? "rgba(240,120,124,0.6)" : "rgba(255,255,255,0.12)";
                const pfg = mism ? "#f0787c" : "rgba(255,255,255,0.9)";
                return (
                  <div key={row.n} className={styles.tr} style={{ flex: "1 1 220px", minWidth: 0, border: `1px solid ${bd}`, borderRadius: "6px", background: "#101114", padding: "16px" }}>
                    <div style={{ display: "flex", justifyContent: "space-between", gap: "8px" }}>
                      <span className="mono" style={{ fontSize: 12, color: "rgba(255,255,255,0.62)" }}>ROW {row.n}</span>
                      <span className="mono" style={{ fontSize: 11, letterSpacing: "0.08em", color: sfg }}>{status}</span>
                    </div>
                    <div style={{ marginTop: 8, fontSize: 15, fontWeight: 500 }}>{event}</div>
                    <div className="mono" style={{ marginTop: 12, fontSize: 11.5, color: "rgba(255,255,255,0.62)" }}>prev <span style={{ color: pfg }}>{row.prev}</span></div>
                    <div className="mono" style={{ marginTop: 2, fontSize: 11.5, color: "rgba(255,255,255,0.62)" }}>hash <span style={{ color: "rgba(255,255,255,0.9)" }}>{hash}</span></div>
                  </div>
                );
              })}
            </div>
            <div style={{ padding: "16px 22px 20px", borderTop: "1px solid rgba(255,255,255,0.08)", fontSize: 15, color: tampered ? "#f0787c" : "rgba(255,255,255,0.72)" }}>
              {tampered
                ? "Chain broken at row 43. Its stored previous hash no longer matches row 42. The verifier raises a security event."
                : "Chain intact. Every row matches the hash stored by the next."}
            </div>
          </div>
        )}

        {/* ── Tab 4: Deployment ── */}
        {tab === 4 && (
          <div className="panel" style={{ marginTop: 0 }}>
            <div style={{ overflowX: "auto", padding: "28px 22px" }}>
              <div style={{ position: "relative", width: DEPLOY_W, height: DEPLOY_H, margin: "0 auto" }}>
                <div
                  style={{
                    position: "absolute", left: DEPLOY_HIGHLIGHT.x, top: DEPLOY_HIGHLIGHT.y,
                    width: DEPLOY_HIGHLIGHT.w, height: DEPLOY_HIGHLIGHT.h, boxSizing: "border-box",
                    background: DEPLOY_HIGHLIGHT.bg, border: `1px solid ${DEPLOY_HIGHLIGHT.border}`, borderRadius: "6px",
                  }}
                />
                {DEPLOY_SEGS.map((s, i) => (
                  <Seg key={i} x={s.x} y={s.y} w={s.w} h={s.h} d={s.d} color={s.color} arrow={s.arrow} hidden={s.hidden} label={s.label} markerId={`arch-dep-ah-${i}`} />
                ))}
                {DEPLOY_BOXES.map((b) => (
                  <Box key={b.title} x={b.x} y={b.y} w={b.w} h={b.h} title={b.title} sub={b.sub} border={b.border} />
                ))}
                {DEPLOY_CAPTIONS.map((c) => (
                  <Caption key={c.text} x={c.x} y={c.y} w={c.w} color={c.color} align={c.align} text={c.text} />
                ))}
                <div
                  className="mono"
                  style={{ position: "absolute", left: DEPLOY_NETWORK_NOTE.x, top: DEPLOY_NETWORK_NOTE.y, width: DEPLOY_NETWORK_NOTE.w, textAlign: "left", fontSize: 12, lineHeight: "16px", color: "#b79fd6" }}
                >
                  {DEPLOY_NETWORK_NOTE.text}
                </div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
