export default async function DocsPage({
  params,
}: {
  params: Promise<{ slug?: string[] }>;
}) {
  const { slug } = await params;
  const path = slug ? slug.join("/") : "index";
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">
        Documentation — <span className="text-fg-2">{path}</span>
      </h1>
    </div>
  );
}
