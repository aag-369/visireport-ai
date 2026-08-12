import { useQuery } from "@tanstack/react-query";
import { api } from "../api/client";
import { useUIStore } from "../store/uiStore";
import { StatusDot } from "./StatusDot";
import { Sparkline } from "./Sparkline";

export function Sidebar() {
  const { data: status } = useQuery({
    queryKey: ["system-status"],
    queryFn: api.getSystemStatus,
    refetchInterval: 5000,
  });

  const {
    confThreshold,
    iouThreshold,
    tileSize,
    overlapMargin,
    setConfThreshold,
    setIouThreshold,
    setTileSize,
    setOverlapMargin,
  } = useUIStore();

  const healthy = (v: unknown) => {
    if (!v || typeof v !== "object") return "unknown";
    const rec = v as Record<string, unknown>;
    if ("healthy" in rec) return rec.healthy ? "healthy" : "error";
    if ("ready" in rec) return rec.ready ? "healthy" : "error";
    return "unknown";
  };

  return (
    <aside className="w-64 shrink-0 bg-bg-secondary border-r border-border p-4 flex flex-col gap-6 overflow-y-auto">
      <div>
        <div className="font-mono text-sm font-bold uppercase tracking-[0.2em] text-accent-cyan">VisiReport</div>
        <div className="font-mono text-[10px] uppercase tracking-[0.2em] text-text-secondary">AI · AOI Console</div>
      </div>

      <div className="visi-panel">
        <div className="visi-panel-header">System Status</div>
        <div className="p-3 flex flex-col gap-2 text-xs">
          <div className="flex items-center justify-between">
            <StatusDot status={healthy(status?.vision_engine)} label="Vision Engine" />
          </div>
          <div className="flex items-center justify-between">
            <StatusDot status={healthy(status?.message_broker)} label="Message Broker" />
          </div>
          <div className="flex items-center justify-between">
            <StatusDot status={healthy(status?.llm_engine)} label="LLM Engine" />
          </div>
          <div className="flex items-center justify-between">
            <StatusDot status={healthy(status?.schema_validator)} label="Schema Validator" />
          </div>
        </div>
      </div>

      <div className="visi-panel">
        <div className="visi-panel-header">Model Config</div>
        <div className="p-3 flex flex-col gap-3 text-[11px] font-mono uppercase text-text-secondary">
          <label className="flex flex-col gap-1">
            Confidence Threshold ({confThreshold.toFixed(2)})
            <input type="range" min={0.05} max={0.95} step={0.05} value={confThreshold} onChange={(e) => setConfThreshold(Number(e.target.value))} />
          </label>
          <label className="flex flex-col gap-1">
            IoU Threshold ({iouThreshold.toFixed(2)})
            <input type="range" min={0.1} max={0.9} step={0.05} value={iouThreshold} onChange={(e) => setIouThreshold(Number(e.target.value))} />
          </label>
          <label className="flex flex-col gap-1">
            Tile Size
            <select className="visi-input" value={tileSize} onChange={(e) => setTileSize(Number(e.target.value))}>
              {[320, 416, 640, 832, 1024].map((v) => (
                <option key={v} value={v}>
                  {v}px
                </option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1">
            Overlap Margin
            <select className="visi-input" value={overlapMargin} onChange={(e) => setOverlapMargin(Number(e.target.value))}>
              {[32, 64, 96, 128].map((v) => (
                <option key={v} value={v}>
                  {v}px
                </option>
              ))}
            </select>
          </label>
        </div>
      </div>

      <div className="visi-panel">
        <div className="visi-panel-header">Queue Monitor</div>
        <div className="p-3 text-xs text-text-secondary">
          <Sparkline data={[2, 3, 1, 4, 2, 5, 3, 2, 1, 3]} />
          <div className="mt-1 font-code text-text-primary">Illustrative - live depth on Compliance tab</div>
        </div>
      </div>

      <div className="mt-auto">
        <span className="visi-iso-badge">ISO 13485:2016 Cl. 8.3 &amp; 8.5.2</span>
      </div>
    </aside>
  );
}
