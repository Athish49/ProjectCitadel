import type { Meta, StoryObj } from "@storybook/nextjs-vite";
import { useState } from "react";
import { FadeIn, SlideIn, Pulse } from "@/components/primitives/motion";

const meta: Meta = {
  title: "Primitives/Motion",
  parameters: { layout: "centered", backgrounds: { default: "dark" } },
};
export default meta;

type Story = StoryObj;

function FadeInDemo() {
  const [key, setKey] = useState(0);
  return (
    <div className="space-y-4 bg-bg-0 p-8">
      <button
        className="rounded border border-bg-3 px-3 py-1 font-mono text-xs text-fg-2 hover:bg-bg-2"
        onClick={() => setKey((k) => k + 1)}
      >
        replay
      </button>
      <FadeIn key={key} className="rounded border border-bg-3 bg-bg-1 px-4 py-3">
        <p className="font-mono text-sm text-fg-0">FadeIn — opacity 0 → 1 · 400ms easeOut</p>
      </FadeIn>
    </div>
  );
}

export const FadeInStory: Story = {
  name: "FadeIn",
  render: () => <FadeInDemo />,
};

function SlideInDemo() {
  const [key, setKey] = useState(0);
  return (
    <div className="space-y-4 bg-bg-0 p-8">
      <button
        className="rounded border border-bg-3 px-3 py-1 font-mono text-xs text-fg-2 hover:bg-bg-2"
        onClick={() => setKey((k) => k + 1)}
      >
        replay
      </button>
      <div className="space-y-2">
        {(["up", "down", "left", "right"] as const).map((dir, i) => (
          <SlideIn key={`${key}-${dir}`} direction={dir} delay={i * 0.05} className="rounded border border-bg-3 bg-bg-1 px-4 py-3">
            <p className="font-mono text-sm text-fg-0">
              SlideIn direction=&quot;{dir}&quot; · 200ms cubic-bezier(0.4,0,0.2,1)
            </p>
          </SlideIn>
        ))}
      </div>
    </div>
  );
}

export const SlideInStory: Story = {
  name: "SlideIn",
  render: () => <SlideInDemo />,
};

export const PulseStory: Story = {
  name: "Pulse",
  render: () => (
    <div className="flex items-center gap-4 bg-bg-0 p-8">
      <Pulse>
        <span className="inline-block h-2 w-2 rounded-full bg-ok" />
      </Pulse>
      <span className="font-mono text-xs text-fg-1">Pulse · 2s ease-in-out loop · used for live status indicators</span>
      <Pulse>
        <span className="inline-block rounded-sm bg-attack px-2 py-0.5 font-mono text-xs font-medium text-bg-0">
          LIVE
        </span>
      </Pulse>
    </div>
  ),
};
