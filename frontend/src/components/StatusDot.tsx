const COLOR_MAP: Record<string, string> = {
  ok: "#00E676",
  healthy: "#00E676",
  degraded: "#FFB020",
  error: "#FF3B3B",
  unhealthy: "#FF3B3B",
  unknown: "#4A5568",
};

export function StatusDot({ status, label }: { status: string; label?: string }) {
  const color = COLOR_MAP[status.toLowerCase()] ?? COLOR_MAP.unknown;
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className="visi-status-dot"
        style={{ backgroundColor: color, boxShadow: `0 0 8px 2px ${color}88` }}
      />
      {label && <span className="font-mono text-xs uppercase tracking-wider text-text-secondary">{label}</span>}
    </span>
  );
}
