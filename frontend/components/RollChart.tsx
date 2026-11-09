export type RollStep = { month: string; rate: number | null };

const W = 360;
const H = 170;
const PAD = { left: 36, right: 12, top: 12, bottom: 26 };

function monthLabel(iso: string, locale: string) {
  return new Date(`${iso}T00:00:00+05:30`).toLocaleDateString(locale, { month: "short", timeZone: "Asia/Kolkata" });
}

/** Line of monthly roll rates with the target as a dashed line. Plain SVG, no chart library. */
export function RollChart({ steps, target, locale }: { steps: RollStep[]; target: number; locale: string }) {
  const max = Math.max(target * 1.6, ...steps.map((s) => s.rate ?? 0)) * 1.1;
  const x = (i: number) => PAD.left + (steps.length > 1 ? (i * (W - PAD.left - PAD.right)) / (steps.length - 1) : 0);
  const y = (v: number) => PAD.top + (1 - v / max) * (H - PAD.top - PAD.bottom);
  const points = steps.flatMap((s, i) => (s.rate === null ? [] : [`${x(i)},${y(s.rate)}`]));
  const ticks = [0, target];

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full" role="img" aria-label="Roll rate by month">
      {ticks.map((v) => (
        <g key={v}>
          <line x1={PAD.left} x2={W - PAD.right} y1={y(v)} y2={y(v)} stroke="var(--line)" />
          <text x={PAD.left - 6} y={y(v) + 4} textAnchor="end" fontSize="10" fill="var(--muted)">
            {Math.round(v * 100)}%
          </text>
        </g>
      ))}
      <line x1={PAD.left} x2={W - PAD.right} y1={y(target)} y2={y(target)} stroke="var(--green)" strokeDasharray="5 4" strokeWidth="1.5" />
      {points.length > 1 && <polyline points={points.join(" ")} fill="none" stroke="var(--accent)" strokeWidth="2.5" />}
      {steps.map((s, i) =>
        s.rate === null ? null : (
          <g key={s.month}>
            <circle cx={x(i)} cy={y(s.rate)} r="4" fill={s.rate > target ? "var(--red)" : "var(--green)"} />
            <text x={x(i)} y={y(s.rate) - 9} textAnchor="middle" fontSize="11" fontWeight="600" fill="var(--ink)">
              {Math.round(s.rate * 100)}%
            </text>
          </g>
        ),
      )}
      {steps.map((s, i) => (
        <text key={`m${s.month}`} x={x(i)} y={H - 8} textAnchor="middle" fontSize="10" fill="var(--muted)">
          {monthLabel(s.month, locale)}
        </text>
      ))}
    </svg>
  );
}
