"use client";

import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { cn } from "@/lib/utils";

interface DocViewerProps {
  content: string;
  className?: string;
}

export function DocViewer({ content, className }: DocViewerProps) {
  return (
    <div className={cn("doc-prose", className)}>
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="mb-6 mt-0 font-mono text-xl font-bold text-fg-0">
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="mb-4 mt-10 border-t border-bg-3 pt-6 font-mono text-base font-semibold text-fg-0">
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="mb-3 mt-6 font-mono text-sm font-semibold text-fg-1">
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="mb-2 mt-4 font-mono text-xs font-semibold uppercase tracking-widest text-fg-2">
              {children}
            </h4>
          ),
          p: ({ children }) => (
            <p className="mb-4 font-mono text-sm leading-relaxed text-fg-1">
              {children}
            </p>
          ),
          a: ({ href, children }) => (
            <a
              href={href}
              className="text-blue-400 underline underline-offset-2 hover:text-blue-300"
              target={href?.startsWith("http") ? "_blank" : undefined}
              rel={href?.startsWith("http") ? "noopener noreferrer" : undefined}
            >
              {children}
            </a>
          ),
          code: ({ children, className: codeClass }) => {
            const isBlock = codeClass?.includes("language-");
            if (isBlock) return null; // handled by pre
            return (
              <code className="rounded bg-bg-2 px-1.5 py-0.5 font-mono text-xs text-warn">
                {children}
              </code>
            );
          },
          pre: ({ children }) => (
            <pre className="mb-4 overflow-x-auto rounded-lg border border-bg-3 bg-bg-2 p-4 font-mono text-xs leading-relaxed text-fg-1">
              {children}
            </pre>
          ),
          ul: ({ children }) => (
            <ul className="mb-4 list-none space-y-1 pl-0">{children}</ul>
          ),
          ol: ({ children }) => (
            <ol className="mb-4 list-decimal space-y-1 pl-5 font-mono text-sm text-fg-1">
              {children}
            </ol>
          ),
          li: ({ children }) => (
            <li className="flex gap-2 font-mono text-sm text-fg-1 before:mt-1.5 before:h-1 before:w-1 before:shrink-0 before:rounded-full before:bg-fg-3">
              <span>{children}</span>
            </li>
          ),
          blockquote: ({ children }) => (
            <blockquote className="mb-4 border-l-2 border-warn pl-4 font-mono text-sm italic text-fg-2">
              {children}
            </blockquote>
          ),
          hr: () => <hr className="my-8 border-bg-3" />,
          strong: ({ children }) => (
            <strong className="font-semibold text-fg-0">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-fg-2">{children}</em>
          ),
          table: ({ children }) => (
            <div className="mb-6 overflow-x-auto rounded-lg border border-bg-3">
              <table className="w-full min-w-[520px] font-mono text-xs">
                {children}
              </table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-bg-2">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-bg-3">{children}</tbody>
          ),
          tr: ({ children }) => <tr>{children}</tr>,
          th: ({ children }) => (
            <th className="px-4 py-2.5 text-left font-semibold uppercase tracking-wider text-fg-3">
              {children}
            </th>
          ),
          td: ({ children }) => (
            <td className="px-4 py-2.5 text-fg-1">{children}</td>
          ),
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
