export default async function SessionReplayPage({
  params,
}: {
  params: Promise<{ traceId: string }>;
}) {
  const { traceId } = await params;
  return (
    <div className="mx-auto max-w-screen-2xl px-4 py-16">
      <h1 className="font-mono text-lg font-semibold text-fg-0">
        Session Replay — <span className="text-fg-2">{traceId}</span>
      </h1>
    </div>
  );
}
