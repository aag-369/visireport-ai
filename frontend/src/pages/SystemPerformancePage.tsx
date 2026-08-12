import { useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid } from "recharts";
import { api } from "../api/client";
import { PanelCard } from "../components/PanelCard";
import { StatusDot } from "../components/StatusDot";

export function SystemPerformancePage() {
  const { data: metrics, isError } = useQuery({ queryKey: ["model-metrics"], queryFn: api.getModelMetrics });
  const { data: status } = useQuery({ queryKey: ["system-status-perf"], queryFn: api.getSystemStatus, refetchInterval: 5000 });

  const perClass: { name: string; map50_95: number }[] = (() => {
    try {
      const raw = (metrics as any)?.per_class_metrics_json;
      if (!raw) return [];
      const parsed = typeof raw === "string" ? JSON.parse(raw) : raw;
      return Object.entries(parsed).map(([k, v]) => ({ name: k, map50_95: Number(v) }));
    } catch {
      return [];
    }
  })();

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      <div className="col-span-2 flex flex-col gap-4">
        <PanelCard title="Model Metrics (from stored training run)">
          {isError ? (
            <div className="text-text-muted text-sm">
              No model_runs record found yet. Metrics are recorded from the actual YOLO training run - see
              backend/data/record_model_run.py.
            </div>
          ) : metrics ? (
            <div className="grid grid-cols-4 gap-3 text-center">
              <MetricTile label="mAP@50" value={metrics.map50} target={0.968} />
              <MetricTile label="mAP@50-95" value={metrics.map50_95} target={0.763} />
              <MetricTile label="Precision" value={metrics.precision} />
              <MetricTile label="Recall" value={metrics.recall} />
              <div className="col-span-4 text-[10px] font-mono text-text-muted text-left mt-2">
                Model {metrics.model_version} · trained on {metrics.dataset} · {metrics.epochs} epochs (CPU) ·{" "}
                {metrics.notes}
              </div>
            </div>
          ) : null}
        </PanelCard>

        <PanelCard title="Per-Class mAP@50-95">
          <ResponsiveContainer width="100%" height={220}>
            <BarChart data={perClass}>
              <CartesianGrid strokeDasharray="3 3" stroke="#252C36" />
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#8896A8" }} />
              <YAxis domain={[0, 1]} tick={{ fontSize: 10, fill: "#8896A8" }} />
              <Tooltip contentStyle={{ background: "#1A1F26", border: "1px solid #252C36" }} />
              <Bar dataKey="map50_95" fill="#00D4FF" name="mAP@50-95" />
            </BarChart>
          </ResponsiveContainer>
          {perClass.length === 0 && <div className="text-text-muted text-xs mt-2">No per-class breakdown recorded.</div>}
        </PanelCard>
      </div>

      <div className="flex flex-col gap-4">
        <PanelCard title="Target SLAs (paper reference)">
          <div className="text-xs font-mono flex flex-col gap-1 text-text-secondary">
            <div>mAP@50 target: 0.968</div>
            <div>mAP@50-95 target: 0.763</div>
            <div>Cycle time target: &lt; 10s / board</div>
            <div>4K tiling support: up to 4096x4096px</div>
            <div className="text-text-muted mt-2">
              These are documented SLA targets from the DeepPCB reference literature, not this deployment's
              achieved numbers - see the Model Metrics panel for actual measured performance.
            </div>
          </div>
        </PanelCard>

        <PanelCard title="System Health">
          <div className="flex flex-col gap-2 text-xs font-mono">
            <StatusDot status={(status?.vision_engine as any)?.ready ? "healthy" : "error"} label="Vision Engine" />
            <StatusDot status={(status?.message_broker as any)?.healthy ? "healthy" : "error"} label="Message Broker" />
            <StatusDot status={(status?.llm_engine as any)?.healthy ? "healthy" : "degraded"} label="LLM Engine" />
            <div className="text-text-primary font-code mt-2">
              CPU: {(status?.vision_engine as any)?.cpu_percent ?? "-"}%
            </div>
            <div className="text-text-primary font-code">
              Memory: {(status?.database as any)?.memory_percent ?? "-"}%
            </div>
            <div className="text-text-muted mt-1">
              Sourced from psutil on the backend host. No GPU is present in this deployment, so GPU
              telemetry is not shown (illustrative-only values would otherwise be required here, which
              this build avoids per the no-fake-data requirement).
            </div>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

function MetricTile({ label, value, target }: { label: string; value: number; target?: number }) {
  return (
    <div className="visi-panel py-3">
      <div className="font-code text-2xl text-accent-cyan">{(value * 100).toFixed(1)}%</div>
      <div className="font-mono text-[10px] uppercase text-text-secondary">{label}</div>
      {target && <div className="font-mono text-[9px] text-text-muted">target {(target * 100).toFixed(1)}%</div>}
    </div>
  );
}
