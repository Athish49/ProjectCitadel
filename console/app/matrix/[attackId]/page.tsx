export default async function AttackDetailPage({
  params,
}: {
  params: Promise<{ attackId: string }>;
}) {
  const { attackId } = await params;
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">
        Attack #{attackId}
      </h1>
    </div>
  );
}
