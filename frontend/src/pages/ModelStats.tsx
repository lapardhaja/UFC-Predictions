import { useModelStats } from "@/hooks/useModelStats";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";

export function ModelStats() {
  const { acc, feat } = useModelStats();

  if (acc.isLoading) return <p className="text-zinc-500 font-mono">Loading model stats…</p>;

  const items = feat.data?.items?.slice(0, 12) ?? [];

  return (
    <div className="space-y-10">
      <h1 className="text-2xl font-bold">Model transparency</h1>
      <div className="grid sm:grid-cols-3 gap-4 font-mono text-sm">
        <Stat label="Holdout accuracy" value={acc.data?.overall_accuracy} fmt="pct" />
        <Stat label="ROC-AUC" value={acc.data?.roc_auc} />
        <Stat label="Brier score" value={acc.data?.brier_score} />
      </div>
      <div>
        <h2 className="text-lg font-semibold mb-4">Feature importance (XGBoost)</h2>
        {items.length === 0 ? (
          <p className="text-zinc-500 text-sm">Train the model to populate importance JSON.</p>
        ) : (
          <div className="h-80 border border-zinc-800 rounded-lg p-2 bg-zinc-950/50">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={items} layout="vertical" margin={{ left: 120 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#27272a" />
                <XAxis type="number" stroke="#71717a" />
                <YAxis type="category" dataKey="feature" width={110} tick={{ fill: "#a1a1aa", fontSize: 10 }} />
                <Tooltip contentStyle={{ background: "#18181b", border: "1px solid #27272a" }} />
                <Bar dataKey="importance" fill="#ff2020" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </div>
    </div>
  );
}

function Stat({ label, value, fmt }: { label: string; value: number | null | undefined; fmt?: "pct" }) {
  const v =
    value == null || Number.isNaN(value)
      ? "—"
      : fmt === "pct"
        ? `${(value * 100).toFixed(1)}%`
        : value.toFixed(3);
  return (
    <div className="border border-zinc-800 rounded-lg p-4 bg-zinc-950/40">
      <div className="text-zinc-500 text-xs uppercase">{label}</div>
      <div className="text-2xl mt-2 text-blood">{v}</div>
    </div>
  );
}
