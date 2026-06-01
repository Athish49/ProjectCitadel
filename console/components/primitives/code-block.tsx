"use client";

import { useEffect, useRef, useState } from "react";
import type { Highlighter } from "shiki";
import { Check, Copy, ExternalLink } from "lucide-react";
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
  githubHref?: string;
  copyable?: boolean;
  className?: string;
}

export function CodeBlock({
  code,
  lang = "typescript",
  filename,
  githubHref,
  copyable = false,
  className,
}: CodeBlockProps) {
  const [html, setHtml] = useState<string | null>(null);
  const [copied, setCopied] = useState(false);
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

  function handleCopy() {
    navigator.clipboard.writeText(code).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  }

  const hasHeader = filename || githubHref || copyable;

  return (
    <div className={cn("overflow-hidden rounded border border-bg-3 bg-bg-1 font-mono text-sm", className)}>
      {hasHeader && (
        <div className="flex items-center gap-2 border-b border-bg-3 px-4 py-2">
          {filename && <span className="flex-1 text-xs text-fg-3">{filename}</span>}
          <div className="ml-auto flex items-center gap-1">
            {githubHref && (
              <a
                href={githubHref}
                target="_blank"
                rel="noopener noreferrer"
                className="rounded p-1 text-fg-3 transition-colors hover:text-fg-1"
                aria-label="Open on GitHub"
              >
                <ExternalLink size={12} />
              </a>
            )}
            {copyable && (
              <button
                type="button"
                onClick={handleCopy}
                className="rounded p-1 text-fg-3 transition-colors hover:text-fg-1"
                aria-label="Copy code"
              >
                {copied ? <Check size={12} className="text-ok" /> : <Copy size={12} />}
              </button>
            )}
          </div>
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
