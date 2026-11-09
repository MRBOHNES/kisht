/** Tiny line of 0-1 values; gaps (null) are skipped. */
export function Sparkline({ values, width = 88, height = 28 }: { values: (number | null)[]; width?: number; height?: number }) {
  const step = values.length > 1 ? width / (values.length - 1) : 0;
  const points = values
    .map((v, i) => (v === null ? null : `${(i * step).toFixed(1)},${(height - 2 - v * (height - 4)).toFixed(1)}`))
    .filter((p): p is string => p !== null);
  return (
    <svg width={width} height={height} viewBox={`0 0 ${width} ${height}`} aria-hidden>
      {points.length > 1 && <polyline points={points.join(" ")} fill="none" stroke="var(--accent)" strokeWidth="2" />}
      {points.length === 1 && <circle cx={points[0].split(",")[0]} cy={points[0].split(",")[1]} r="2.5" fill="var(--accent)" />}
    </svg>
  );
}
