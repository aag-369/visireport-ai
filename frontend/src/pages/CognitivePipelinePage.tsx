import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { PanelCard } from "../components/PanelCard";
import { StatusDot } from "../components/StatusDot";
import { useUIStore } from "../store/uiStore";

export function CognitivePipelinePage() {
  const { activeInspectionId } = useUIStore();
  const [showRaw, setShowRaw] = useState(false);
  const qc = useQueryClient();

  const { data: inspection } = useQuery({
    queryKey: ["inspection", activeInspectionId],
    queryFn: () => api.getInspection(activeInspectionId as number),
    enabled: activeInspectionId != null,
  });

  const { data: narrative } = useQuery({
    queryKey: ["narrative", activeInspectionId],
    queryFn: () => api.getNarrative(activeInspectionId as number),
    enabled: activeInspectionId != null,
    refetchInterval: (query) => (query.state.data?.status === "PENDING" ? 2000 : false),
  });

  const regenerate = useMutation({
    mutationFn: () => api.regenerateNarrative(activeInspectionId as number),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["narrative", activeInspectionId] }),
  });

  if (activeInspectionId == null || !inspection) {
    return (
      <div className="p-4">
        <PanelCard title="Cognitive Pipeline">
          <div className="text-text-muted text-sm">Run an inspection first.</div>
        </PanelCard>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      <div className="flex flex-col gap-4">
        <PanelCard title="Pipeline Status">
          <div className="flex flex-col gap-2 text-xs font-mono">
            <div className="flex justify-between items-center">
              <span className="uppercase text-text-secondary">Schema Validation</span>
              <StatusDot status={inspection.schema_valid ? "healthy" : "error"} label={inspection.schema_valid ? "VALID" : "INVALID"} />
            </div>
            <div className="flex justify-between items-center">
              <span className="uppercase text-text-secondary">RabbitMQ Delivery</span>
              <StatusDot status={inspection.status === "COMPLETE" ? "healthy" : "unknown"} label={inspection.status} />
            </div>
            <div className="flex justify-between items-center">
              <span className="uppercase text-text-secondary">LLM Synthesis</span>
              <StatusDot
                status={narrative?.status === "READY" ? "healthy" : narrative?.status === "FAILED" ? "error" : "degraded"}
                label={narrative?.status ?? "PENDING"}
              />
            </div>
          </div>
        </PanelCard>

        <PanelCard title="Raw Payload" actions={<button className="text-[10px] font-mono text-accent-cyan" onClick={() => setShowRaw((s) => !s)}>{showRaw ? "hide" : "show"}</button>}>
          {showRaw ? (
            <pre className="visi-terminal text-[10px]" style={{ height: 240 }}>
              {JSON.stringify(inspection, null, 2)}
            </pre>
          ) : (
            <div className="text-text-muted text-xs">Collapsed - click "show" to view the VISIREPORT_SCHEMA payload.</div>
          )}
        </PanelCard>
      </div>

      <div className="col-span-2 flex flex-col gap-4">
        <PanelCard
          title="NCR Narrative"
          actions={
            <button className="visi-btn" type="button" disabled={regenerate.isPending} onClick={() => regenerate.mutate()}>
              {regenerate.isPending ? "Regenerating..." : "Regenerate"}
            </button>
          }
        >
          {narrative?.status === "READY" ? (
            <textarea className="visi-input w-full font-sans normal-case" rows={6} defaultValue={narrative.narrative_text ?? ""} />
          ) : narrative?.status === "FAILED" ? (
            <div className="text-accent-crimson text-xs font-mono">
              LLM synthesis failed: {narrative.error_detail}
              <div className="text-text-muted mt-1">
                Set ANTHROPIC_API_KEY or OPENAI_API_KEY in your .env and click Regenerate.
              </div>
            </div>
          ) : (
            <div className="text-text-muted text-sm">Narrative synthesis pending - the worker will pick this up from RabbitMQ.</div>
          )}
        </PanelCard>

        <PanelCard title="Root Cause Hypothesis">
          <div className="text-sm text-text-primary">{narrative?.root_cause_text ?? <span className="text-text-muted">-</span>}</div>
        </PanelCard>

        <div className="grid grid-cols-3 gap-3">
          <CapaCard title="Immediate Containment" text={narrative?.capa?.immediate_containment} color="#FF3B3B" />
          <CapaCard title="Root Cause Elimination" text={narrative?.capa?.root_cause_elimination} color="#FFB020" />
          <CapaCard title="Preventive Measure" text={narrative?.capa?.preventive_measure} color="#00E676" />
        </div>
      </div>
    </div>
  );
}

function CapaCard({ title, text, color }: { title: string; text?: string; color: string }) {
  return (
    <div className="visi-panel">
      <div className="visi-panel-header" style={{ color }}>
        {title}
      </div>
      <div className="p-3 text-xs text-text-primary min-h-[80px]">{text ?? <span className="text-text-muted">-</span>}</div>
    </div>
  );
}
