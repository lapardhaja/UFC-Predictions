import { Link } from "react-router-dom";
import type { EventSummary } from "@/types";

export function EventCard({ event }: { event: EventSummary }) {
  const dateStr = event.date ? new Date(event.date).toLocaleDateString() : "TBA";
  return (
    <Link
      to={`/events/${event.event_id}`}
      className="block border border-zinc-800 rounded-lg p-4 hover:border-blood/60 bg-zinc-950/50 transition"
    >
      <div className="text-xs uppercase tracking-widest text-zinc-500 font-mono">{dateStr}</div>
      <h2 className="text-lg font-semibold mt-1">{event.event_name}</h2>
      <p className="text-sm text-zinc-400 mt-2">{event.location || "Location TBA"}</p>
      <div className="mt-4 flex justify-between items-center">
        <span className="text-sm font-mono text-zinc-500">{event.fight_count} fights</span>
        <span className="text-blood text-sm font-medium">View card →</span>
      </div>
    </Link>
  );
}
