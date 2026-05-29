import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { MonoBlock } from "@/components/primitives/mono-block";

const meta: Meta<typeof MonoBlock> = {
  title: "Primitives/MonoBlock",
  component: MonoBlock,
  parameters: { layout: "padded", backgrounds: { default: "dark" } },
  argTypes: {
    severity: {
      control: "select",
      options: ["ok", "warn", "alert", "attack", "trust", "audit", "neutral"],
    },
  },
};
export default meta;

type Story = StoryObj<typeof MonoBlock>;

export const Default: Story = {
  args: {
    timestamp: "14:32:07.441",
    severity: "ok",
    label: "P8",
    message: "Envelope verified · agent=claims-processor · sig=3045022100…",
  },
};

export const AttackBlocked: Story = {
  args: {
    timestamp: "14:32:08.112",
    severity: "alert",
    label: "BLOCK",
    message: "Prompt injection attempt detected · pattern=instruction-override · action=REJECT",
  },
};

export const AuditFeed: Story = {
  render: () => (
    <div className="space-y-0.5 bg-bg-0 p-4">
      {[
        { ts: "14:32:07.441", sev: "ok"     as const, label: "P8",    msg: "Envelope verified · agent=claims-processor" },
        { ts: "14:32:07.822", sev: "trust"  as const, label: "P2",    msg: "Capability token granted · scope=claims:read" },
        { ts: "14:32:08.112", sev: "alert"  as const, label: "BLOCK", msg: "Prompt injection blocked · pattern=instruction-override" },
        { ts: "14:32:08.350", sev: "attack" as const, label: "ATK",   msg: "Adversarial agent probing token endpoint · attempt=3/5" },
        { ts: "14:32:08.901", sev: "warn"   as const, label: "P5",    msg: "Rate limit approaching · agent=data-extractor · 87/100 rps" },
        { ts: "14:32:09.210", sev: "audit"  as const, label: "LOG",   msg: "Claim #CC-2041 forwarded to adjudicator · confidence=0.91" },
        { ts: "14:32:09.874", sev: "ok"     as const, label: "P8",    msg: "Envelope verified · agent=adjudicator" },
      ].map((row) => (
        <MonoBlock
          key={row.ts}
          timestamp={row.ts}
          severity={row.sev}
          label={row.label}
          message={row.msg}
        />
      ))}
    </div>
  ),
};

export const NoMetadata: Story = {
  args: {
    message: "system booted · version=3.1.2 · env=preview",
    severity: "neutral",
  },
};
