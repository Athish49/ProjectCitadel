import type { Metadata } from "next";
import { PlaygroundApp } from "@/components/playground/playground-app";

export const metadata: Metadata = {
  title: "Attack Playground — Project Citadel",
};

export default function PlaygroundPage() {
  return <PlaygroundApp />;
}
