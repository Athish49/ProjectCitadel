"use client";

import { useSearchParams } from "next/navigation";
import { Header } from "./header";

export function ConditionalHeader() {
  const params = useSearchParams();
  if (params.get("embed") === "1") return null;
  return <Header />;
}
