import type { Metadata } from "next";
import { PlaygroundApp } from "@/components/playground/playground-app";

export const metadata: Metadata = {
  title: "Playground — Project Citadel",
  description:
    "A working claims assistant behind seven defence layers. Sign in as a customer, ask or attack, and watch each layer decide.",
};

export default function PlaygroundPage() {
  return <PlaygroundApp />;
}
