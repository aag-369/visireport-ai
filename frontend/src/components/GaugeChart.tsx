/** SVG gauge with colored threshold bands and a needle - used for queue
 * depth and cycle-time SLA callouts. */
export function GaugeChart({
  value,
  max,
  label,
  unit = "",
  bands = [
    { to: 0.6, color: "#00E676" },
    { to: 0.85, color: "#FFB020" },
    { to: 1, color: "#FF3B3B" },
  ],
}: {
  value: number;
  max: number;
  label: string;
  unit?: string;
  bands?: { to: number; color: string }[];
}) {
  const size = 160;
  const cx = size / 2;
  const cy = size / 2 + 10;
  const radius = 60;
  const startAngle = -180;
  const endAngle = 0;

  const pct = Math.max(0, Math.min(1, value / max));
  const angle = startAngle + pct * (endAngle - startAngle);
  const rad = (deg: number) => (deg * Math.PI) / 180;
  const needleX = cx + radius * 0.85 * Math.cos(rad(angle));
  const needleY = cy + radius * 0.85 * Math.sin(rad(angle));

  const arcPath = (fromPct: number, toPct: number, color: string, key: string) => {
    const a0 = startAngle + fromPct * (endAngle - startAngle);
    const a1 = startAngle + toPct * (endAngle - startAngle);
    const x0 = cx + radius * Math.cos(rad(a0));
    const y0 = cy + radius * Math.sin(rad(a0));
    const x1 = cx + radius * Math.cos(rad(a1));
    const y1 = cy + radius * Math.sin(rad(a1));
    const largeArc = a1 - a0 > 180 ? 1 : 0;
    return (
      <path
        key={key}
        d={`M ${x0} ${y0} A ${radius} ${radius} 0 ${largeArc} 1 ${x1} ${y1}`}
        stroke={color}
        strokeWidth={12}
        fill="none"
        strokeLinecap="butt"
      />
    );
  };

  let prev = 0;
  const arcs = bands.map((b, i) => {
    const el = arcPath(prev, b.to, b.color, `band-${i}`);
    prev = b.to;
    return el;
  });

  return (
    <div className="flex flex-col items-center">
      <svg width={size} height={size / 2 + 30} viewBox={`0 0 ${size} ${size / 2 + 30}`}>
        {arcs}
        <line x1={cx} y1={cy} x2={needleX} y2={needleY} stroke="#E8EDF5" strokeWidth={2} />
        <circle cx={cx} cy={cy} r={4} fill="#E8EDF5" />
      </svg>
      <div className="font-code text-lg text-text-primary -mt-2">
        {value}
        <span className="text-text-secondary text-xs">{unit}</span>
      </div>
      <div className="font-mono text-[10px] uppercase tracking-wider text-text-secondary">{label}</div>
    </div>
  );
}
