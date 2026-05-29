import type { Meta, StoryObj } from "@storybook/nextjs-vite";

const meta: Meta = {
  title: "Primitives/Typography",
  parameters: { layout: "padded", backgrounds: { default: "dark" } },
};
export default meta;

type Story = StoryObj;

export const TypeScale: Story = {
  render: () => (
    <div className="space-y-6 bg-bg-0 p-8">
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">display — text-3xl font-semibold tracking-tight</p>
        <h1 className="font-sans text-3xl font-semibold tracking-tight text-fg-0">
          Resilient Agentic AI
        </h1>
      </div>
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">heading — text-xl font-semibold</p>
        <h2 className="font-sans text-xl font-semibold text-fg-0">Defense Pattern Library</h2>
      </div>
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">subheading — text-base font-medium</p>
        <h3 className="font-sans text-base font-medium text-fg-1">P8 — Signed Inter-Agent Envelopes</h3>
      </div>
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">body — text-sm (15px base)</p>
        <p className="font-sans text-sm leading-relaxed text-fg-1">
          Every message crossing an agent boundary is signed with a secp256k1 private key.
          Recipients verify the envelope before processing any payload, rejecting unknown signers.
        </p>
      </div>
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">caption — text-xs text-fg-2</p>
        <p className="font-sans text-xs text-fg-2">Last updated 2026-05-29 · 79 attack categories</p>
      </div>
      <hr className="border-bg-3" />
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">mono heading — font-mono text-sm font-semibold tracking-tight</p>
        <span className="font-mono text-sm font-semibold tracking-tight text-fg-0">SECURECLAIM AI / Resilience Console</span>
      </div>
      <div>
        <p className="mb-1 font-mono text-xs text-fg-3">mono body — font-mono text-xs</p>
        <span className="font-mono text-xs text-fg-1">agent=claims-processor · trace=7a4f2b · status=BLOCKED</span>
      </div>
    </div>
  ),
};

const SIGNAL_ROWS = [
  { dot: "bg-ok",     text: "text-ok",     label: "OK",     token: "--ok"     },
  { dot: "bg-warn",   text: "text-warn",   label: "WARN",   token: "--warn"   },
  { dot: "bg-alert",  text: "text-alert",  label: "ALERT",  token: "--alert"  },
  { dot: "bg-attack", text: "text-attack", label: "ATTACK", token: "--attack" },
  { dot: "bg-trust",  text: "text-trust",  label: "TRUST",  token: "--trust"  },
  { dot: "bg-audit",  text: "text-audit",  label: "AUDIT",  token: "--audit"  },
] as const;

export const SignalColors: Story = {
  render: () => (
    <div className="space-y-3 bg-bg-0 p-8">
      {SIGNAL_ROWS.map(({ dot, text, label, token }) => (
        <div key={label} className="flex items-center gap-3">
          <span className={`h-2 w-2 rounded-full ${dot}`} />
          <span className={`font-mono text-xs ${text}`}>{label}</span>
          <span className="font-mono text-xs text-fg-3">{token}</span>
        </div>
      ))}
    </div>
  ),
};

const LABEL_ROWS = [
  { cls: "text-label-public",       border: "border-label-public",       name: "public"       },
  { cls: "text-label-personal",     border: "border-label-personal",     name: "personal"     },
  { cls: "text-label-confidential", border: "border-label-confidential", name: "confidential" },
  { cls: "text-label-secret",       border: "border-label-secret",       name: "secret"       },
  { cls: "text-label-untrusted",    border: "border-label-untrusted",    name: "untrusted"    },
] as const;

export const TrustLabels: Story = {
  render: () => (
    <div className="flex flex-wrap gap-3 bg-bg-0 p-8">
      {LABEL_ROWS.map(({ cls, border, name }) => (
        <span
          key={name}
          className={`rounded-sm border px-2 py-0.5 font-mono text-xs font-medium uppercase tracking-wide ${cls} ${border}`}
        >
          {name}
        </span>
      ))}
    </div>
  ),
};
