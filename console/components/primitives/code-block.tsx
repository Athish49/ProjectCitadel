"use client";

import { useEffect, useRef, useState } from "react";
import type { Highlighter } from "shiki";
import { cn } from "@/lib/utils";

let highlighterPromise: Promise<Highlighter> | null = null;

function getHighlighter() {
  if (!highlighterPromise) {
    highlighterPromise = import("shiki").then(({ createHighlighter }) =>
      createHighlighter({
        themes: ["github-dark"],
        langs: ["typescript", "python", "bash", "json", "yaml"],
      })
    );
  }
  return highlighterPromise;
}

interface CodeBlockProps {
  code: string;
  lang?: "typescript" | "python" | "bash" | "json" | "yaml";
  filename?: string;
  className?: string;
}

export function CodeBlock({ code, lang = "typescript", filename, className }: CodeBlockProps) {
  const [html, setHtml] = useState<string | null>(null);
  const mountedRef = useRef(true);

  useEffect(() => {
    mountedRef.current = true;
    getHighlighter().then((hl) => {
      if (!mountedRef.current) return;
      const highlighted = hl.codeToHtml(code, { lang, theme: "github-dark" });
      setHtml(highlighted);
    });
    return () => {
      mountedRef.current = false;
    };
  }, [code, lang]);

  return (
    <div className={cn("overflow-hidden rounded border border-bg-3 bg-bg-1 font-mono text-sm", className)}>
      {filename && (
        <div className="flex items-center gap-2 border-b border-bg-3 px-4 py-2">
          <span className="text-xs text-fg-3">{filename}</span>
        </div>
      )}
      {html ? (
        <div
          className="overflow-x-auto p-4 [&>pre]:!bg-transparent [&>pre]:!m-0 [&>pre]:!p-0"
          dangerouslySetInnerHTML={{ __html: html }}
        />
      ) : (
        <pre className="overflow-x-auto p-4 text-fg-2">{code}</pre>
      )}
    </div>
  );
}
