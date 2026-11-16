import { MoreLink } from "./more-link";

interface SectionHeaderProps {
  eyebrow: string;
  title: string;
  lead: string;
  more: { label: string; href: string; external?: boolean };
}

/** The repeated "01 — Architecture / headline / lead / more-link" header row
 * used at the top of sections 01 through 05 in Main.dc.html. */
export function SectionHeader({ eyebrow, title, lead, more }: SectionHeaderProps) {
  return (
    <div
      style={{
        display: "flex",
        flexWrap: "wrap",
        justifyContent: "space-between",
        alignItems: "flex-end",
        gap: "24px 48px",
      }}
    >
      <div data-rv style={{ maxWidth: "620px" }}>
        <div className="eb">{eyebrow}</div>
        <h2
          style={{
            margin: "18px 0 0",
            fontSize: "clamp(30px,3.8vw,48px)",
            lineHeight: 1.06,
            letterSpacing: "-0.03em",
            fontWeight: 600,
            color: "rgba(255,255,255,0.97)",
          }}
        >
          {title}
        </h2>
        <p style={{ margin: "16px 0 0", fontSize: "17px", color: "rgba(255,255,255,0.7)" }}>{lead}</p>
      </div>
      <MoreLink href={more.href} external={more.external} reveal>
        {more.label}
      </MoreLink>
    </div>
  );
}
