import { useEvents } from "@/hooks/useEvents";
import { EventCard } from "@/components/EventCard";

export function Home() {
  const { data, isLoading, error } = useEvents();

  if (isLoading) return <p className="text-zinc-500 font-mono">Loading upcoming events…</p>;
  if (error) return <p className="text-blood">Failed to load events</p>;
  if (!data?.length) {
    return (
      <div className="text-center py-20 text-zinc-500">
        <p>No upcoming events in database.</p>
        <p className="text-sm mt-2 font-mono">POST /api/v1/admin/refresh-events with admin key</p>
      </div>
    );
  }

  return (
    <div>
      <h1 className="text-2xl font-bold tracking-tight">Upcoming events</h1>
      <p className="text-zinc-500 mt-2 max-w-xl">
        Win probabilities use the trained ensemble when <code className="text-blood">ml/models/production.pkl</code>{" "}
        exists; otherwise a simple record heuristic is shown.
      </p>
      <div className="mt-8 grid sm:grid-cols-2 gap-4">
        {data.map((e) => (
          <EventCard key={e.event_id} event={e} />
        ))}
      </div>
    </div>
  );
}
