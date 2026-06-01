import { notFound } from "next/navigation";
import Link from "next/link";
import { DOCS, getDocBySlug, getDocContent } from "@/lib/data/docs";
import { DocViewer } from "@/components/docs/doc-viewer";
import { cn } from "@/lib/utils";

export function generateStaticParams() {
  return [
    { slug: undefined },
    ...DOCS.map((d) => ({ slug: [d.slug] })),
  ];
}

export default async function DocsPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  const slugStr = slug?.[0];

  if (slugStr) {
    const doc = getDocBySlug(slugStr);
    if (!doc) notFound();

    const content = getDocContent(doc.filename);

    return (
      <div className="mx-auto flex max-w-screen-xl gap-0 px-0">
        {/* Sidebar */}
        <aside className="sticky top-12 hidden h-[calc(100vh-48px)] w-56 shrink-0 overflow-y-auto border-r border-bg-3 lg:block">
          <div className="px-4 py-6">
            <p className="mb-4 font-mono text-xs font-semibold uppercase tracking-widest text-fg-3">
              Documents
            </p>
            <nav className="flex flex-col gap-0.5">
              {DOCS.map((d) => (
                <Link
                  key={d.slug}
                  href={`/docs/${d.slug}`}
                  className={cn(
                    "flex items-center gap-2 rounded px-2 py-1.5 font-mono text-xs transition-colors",
                    d.slug === slugStr
                      ? "bg-bg-2 text-fg-0"
                      : "text-fg-2 hover:bg-bg-2 hover:text-fg-1"
                  )}
                >
                  <span className="text-fg-3">{d.number}</span>
                  <span>{d.shortTitle}</span>
                </Link>
              ))}
            </nav>
            <div className="mt-6 border-t border-bg-3 pt-4">
              <Link
                href="/docs"
                className="font-mono text-xs text-fg-3 hover:text-fg-2"
              >
                ← All docs
              </Link>
            </div>
          </div>
        </aside>

        {/* Content */}
        <main className="min-w-0 flex-1 px-6 py-8 lg:px-10">
          {/* Mobile doc nav */}
          <div className="mb-6 lg:hidden">
            <div className="flex flex-wrap gap-1.5">
              {DOCS.map((d) => (
                <Link
                  key={d.slug}
                  href={`/docs/${d.slug}`}
                  className={cn(
                    "rounded px-2 py-1 font-mono text-xs transition-colors",
                    d.slug === slugStr
                      ? "bg-bg-2 text-fg-0"
                      : "text-fg-2 hover:bg-bg-2"
                  )}
                >
                  {d.number} {d.shortTitle}
                </Link>
              ))}
            </div>
          </div>

          <DocViewer content={content} />
        </main>
      </div>
    );
  }

  // Index page
  return (
    <div className="mx-auto max-w-screen-xl px-4 py-10">
      <div className="mb-8">
        <h1 className="font-mono text-lg font-semibold text-fg-0">
          Documentation Hub
        </h1>
        <p className="mt-1 font-mono text-sm text-fg-3">
          6 internal docs · architecture, security, data model, roadmap, console spec
        </p>
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {DOCS.map((doc) => (
          <Link
            key={doc.slug}
            href={`/docs/${doc.slug}`}
            className="group rounded-lg border border-bg-3 bg-bg-1 p-5 transition-colors hover:border-bg-2 hover:bg-bg-2"
          >
            <div className="mb-1 flex items-baseline gap-2">
              <span className="font-mono text-xs text-fg-3">{doc.number}</span>
              <span className="font-mono text-sm font-semibold text-fg-0 group-hover:text-fg-0">
                {doc.shortTitle}
              </span>
            </div>
            <p className="font-mono text-xs leading-relaxed text-fg-2">
              {doc.description}
            </p>
          </Link>
        ))}
      </div>
    </div>
  );
}
