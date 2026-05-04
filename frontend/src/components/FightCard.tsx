import { Link } from "react-router-dom";
import { WinProbabilityBar } from "./WinProbabilityBar";

interface PredFighter {
  name: string;
  win_probability: number;
  confidence: string;
}

interface Props {
  fightId: string;
  weightClass?: string | null;
  eventLabel?: string;
  dateLabel?: string;
  fighterA: { name: string; fighter_id?: string };
  fighterB: { name: string; fighter_id?: string };
  prediction?: {
    fighter_a: PredFighter;
    fighter_b: PredFighter;
    top_factors?: { feature: string; impact: string; favor: string }[];
    predicted_method?: string;
    model_version?: string;
  };
}

export function FightCard({
  fightId,
  weightClass,
  eventLabel,
  dateLabel,
  fighterA,
  fighterB,
  prediction,
}: Props) {
  const pa = prediction?.fighter_a.win_probability ?? 0.5;
  const pct = pa * 100;
  const fav = pa >= 0.5 ? fighterA.name : fighterB.name;
  const conf = prediction?.fighter_a.confidence ?? "Low";

  return (
    <div className="border border-zinc-800 rounded-xl p-5 bg-gradient-to-b from-zinc-900/40 to-black">
      <div className="text-xs font-mono text-zinc-500 uppercase tracking-wider">
        {[weightClass, eventLabel, dateLabel].filter(Boolean).join(" · ")}
      </div>
      <div className="mt-4 grid grid-cols-[1fr_auto_1fr] gap-3 items-center">
        <div className="text-right">
          {fighterA.fighter_id ? (
            <Link to={`/fighters/${fighterA.fighter_id}`} className="font-semibold hover:text-blood">
              {fighterA.name}
            </Link>
          ) : (
            <span className="font-semibold">{fighterA.name}</span>
          )}
        </div>
        <span className="text-zinc-600 text-sm">vs</span>
        <div>
          {fighterB.fighter_id ? (
            <Link to={`/fighters/${fighterB.fighter_id}`} className="font-semibold hover:text-blood">
              {fighterB.name}
            </Link>
          ) : (
            <span className="font-semibold">{fighterB.name}</span>
          )}
        </div>
      </div>
      <div className="mt-4">
        <WinProbabilityBar leftPct={pct} />
        <div className="flex justify-between text-xs font-mono mt-1 text-zinc-400">
          <span>{(pa * 100).toFixed(0)}%</span>
          <span>{((1 - pa) * 100).toFixed(0)}%</span>
        </div>
      </div>
      <div className="mt-3 text-sm">
        <span className="text-blood font-mono">↑</span>{" "}
        <span className="text-zinc-300">
          Prediction: <strong>{fav}</strong>
        </span>
        <span className="text-zinc-500 ml-2">· Confidence: {conf}</span>
      </div>
      {prediction?.top_factors && prediction.top_factors.length > 0 && (
        <div className="mt-4 border-t border-zinc-800 pt-3">
          <div className="text-xs uppercase text-zinc-500 font-mono mb-2">Key edges</div>
          <ul className="text-sm space-y-1 text-zinc-400">
            {prediction.top_factors.slice(0, 3).map((t) => (
              <li key={t.feature} className="font-mono text-xs">
                <span className="text-zinc-200">{t.feature}</span> {t.impact}{" "}
                <span className="text-blood">{t.favor}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
      <div className="mt-3 text-xs text-zinc-600 font-mono">
        fight_id: {fightId}
        {prediction?.predicted_method && ` · method: ${prediction.predicted_method}`}
        {prediction?.model_version && ` · ${prediction.model_version}`}
      </div>
    </div>
  );
}
