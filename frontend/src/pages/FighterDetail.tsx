import { useParams } from "react-router-dom";
import { useFighter } from "@/hooks/useFighter";
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
} from "recharts";

export function FighterDetail() {
  const { fighterId } = useParams();
  const { data, isLoading, error } = useFighter(fighterId);

  if (isLoading) return <p className="text-zinc-500 font-mono">Loading fighter…</p>;
  if (error || !data) return <p className="text-blood">Fighter not found</p>;

  const radar = [
    { stat: "Wins", value: data.wins * 10 },
    { stat: "Reach", value: (data.reach_cm || 170) - 150 },
    { stat: "Height", value: (data.height_cm || 175) - 160 },
    { stat: "Exp", value: data.wins + data.losses },
  ];

  return (
    <div className="grid md:grid-cols-2 gap-8">
      <div>
        <h1 className="text-3xl font-bold">{data.name}</h1>
        <p className="font-mono text-blood mt-2">
          {data.wins}-{data.losses}-{data.draws}
          {data.nc ? ` (${data.nc} NC)` : ""}
        </p>
        <dl className="mt-6 space-y-2 text-sm font-mono text-zinc-400">
          <div className="flex justify-between border-b border-zinc-800 py-2">
            <dt>Height</dt>
            <dd>{data.height_cm ?? "—"} cm</dd>
          </div>
          <div className="flex justify-between border-b border-zinc-800 py-2">
            <dt>Reach</dt>
            <dd>{data.reach_cm ?? "—"} cm</dd>
          </div>
          <div className="flex justify-between border-b border-zinc-800 py-2">
            <dt>Stance</dt>
            <dd>{data.stance ?? "—"}</dd>
          </div>
        </dl>
      </div>
      <div className="h-72 border border-zinc-800 rounded-lg p-2 bg-zinc-950/50">
        <ResponsiveContainer width="100%" height="100%">
          <RadarChart data={radar}>
            <PolarGrid stroke="#333" />
            <PolarAngleAxis dataKey="stat" tick={{ fill: "#a1a1aa", fontSize: 11 }} />
            <PolarRadiusAxis angle={30} domain={[0, "auto"]} tick={false} />
            <Radar name={data.name} dataKey="value" stroke="#ff2020" fill="#ff2020" fillOpacity={0.25} />
          </RadarChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
