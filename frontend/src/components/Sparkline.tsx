export function Sparkline({ data, color = "#00D4FF", width = 140, height = 36 }: { data: number[]; color?: string; width?: number; height?: number }) {
  if (data.length < 2) return <div className="text-text-muted text-xs font-code">insufficient data</div>;
  const max = Math.max(...data, 1);
  const min = Math.min(...data, 0);
  const range = max - min || 1;
  const step = width / (data.length - 1);
  const points = data.map((v, i) => `${i * step},${height - ((v - min) / range) * height}`).join(" ");
  return (
    <svg width={width} height={height}>
      <polyline points={points} fill="none" stroke={color} strokeWidth={1.5} />
    </svg>
  );
}
