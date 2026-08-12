import { useEffect, useRef } from "react";
import type { ScanLogEntry } from "../hooks/useInspectionSocket";

const LEVEL_COLOR: Record<ScanLogEntry["level"], string> = {
  info: "#00FF88",
  success: "#00E676",
  warn: "#FFB020",
  error: "#FF3B3B",
};

export function TerminalLog({ entries, height = 260 }: { entries: ScanLogEntry[]; height?: number }) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (ref.current) ref.current.scrollTop = ref.current.scrollHeight;
  }, [entries]);

  return (
    <div ref={ref} className="visi-terminal" style={{ height }}>
      {entries.length === 0 && <div className="text-text-muted">Awaiting scan activity...</div>}
      {entries.map((e, i) => (
        <div key={i} style={{ color: LEVEL_COLOR[e.level] }}>
          <span className="text-text-muted">[{e.timestamp}]</span> {e.message}
        </div>
      ))}
    </div>
  );
}
