import { useParams } from "react-router-dom";
import { FightCard } from "@/components/FightCard";
import { useEvent } from "@/hooks/useEvents";
import { useFight } from "@/hooks/useFight";
import type { FightSummary } from "@/types";

export function EventDetail() {
  const { eventId } = useParams();
  const { data, isLoading, error } = useEvent(eventId);

  if (isLoading) return <p className="text-zinc-500 font-mono">Loading event…</p>;
  if (error || !data) return <p className="text-blood">Event not found</p>;

  return (
    <div>
      <h1 className="text-2xl font-bold">{data.event_name}</h1>
      <p className="text-zinc-400 mt-1 font-mono text-sm">{data.location}</p>
      <div className="mt-8 grid gap-4">
        {data.fights.map((f) => (
          <FightCardLoader key={f.fight_id} fightId={f.fight_id} summary={f} eventName={data.event_name} />
        ))}
      </div>
    </div>
  );
}

function FightCardLoader({
  fightId,
  summary,
  eventName,
}: {
  fightId: string;
  summary: FightSummary;
  eventName: string;
}) {
  const { data, isLoading } = useFight(fightId);
  const pred = data?.prediction as
    | {
        fighter_a: { name: string; win_probability: number; confidence: string };
        fighter_b: { name: string; win_probability: number; confidence: string };
        top_factors?: { feature: string; impact: string; favor: string }[];
        predicted_method?: string;
        model_version?: string;
      }
    | undefined;

  if (isLoading) {
    return <div className="border border-zinc-800 rounded-xl p-5 animate-pulse h-48 bg-zinc-900/30" />;
  }

  return (
    <FightCard
      fightId={fightId}
      weightClass={summary.weight_class}
      eventLabel={eventName}
      fighterA={{ ...summary.fighter_a }}
      fighterB={{ ...summary.fighter_b }}
      prediction={pred}
    />
  );
}
