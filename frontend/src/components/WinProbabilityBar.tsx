interface Props {
  leftPct: number;
}

export function WinProbabilityBar({ leftPct }: Props) {
  const p = Math.min(100, Math.max(0, leftPct));
  return (
    <div className="h-3 w-full bg-zinc-900 rounded overflow-hidden flex">
      <div
        className="h-full bg-blood transition-all duration-500"
        style={{ width: `${p}%` }}
        data-testid="prob-left"
      />
      <div className="flex-1 bg-zinc-800" />
    </div>
  );
}
