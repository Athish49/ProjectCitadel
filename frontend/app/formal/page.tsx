import type { Metadata } from "next";
import { FormalPage } from "@/components/formal/formal-page";

export const metadata: Metadata = {
  title: "Formal verification — Project Citadel",
  description: "The claim workflow is specified in TLA+ and model-checked in every state it can ever reach — run the real BFS checker live.",
};

export default function Page() {
  return <FormalPage />;
}
