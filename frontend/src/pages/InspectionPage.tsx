import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import { useMutation, useQuery } from "@tanstack/react-query";
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from "recharts";
import { api } from "../api/client";
import { PanelCard } from "../components/PanelCard";
import { TerminalLog } from "../components/TerminalLog";
import { TileGridOverlay } from "../components/TileGridOverlay";
import { ZoomControls } from "../components/ZoomControls";
import { SeverityBadge } from "../components/DefectBadge";
import { useInspectionSocket } from "../hooks/useInspectionSocket";
import { useUIStore } from "../store/uiStore";
import { defectColors, severityColors, type DefectClass, type Severity } from "../theme/tokens";

export function InspectionPage() {
  const [boardId, setBoardId] = useState("PCBA-MED-001");
  const { activeInspectionId, setActiveInspectionId, confThreshold, iouThreshold, tileSize, overlapMargin, zoom, offsetX, offsetY, showTileGrid } =
    useUIStore();
  const { log, connected } = useInspectionSocket(activeInspectionId);

  const { data: inspection, refetch } = useQuery({
    queryKey: ["inspection", activeInspectionId],
    queryFn: () => api.getInspection(activeInspectionId as number),
    enabled: activeInspectionId != null,
    refetchInterval: (query) => (query.state.data?.status === "PROCESSING" ? 1500 : false),
  });

  const uploadMutation = useMutation({
    mutationFn: async (file: File) =>
      api.uploadInspection(boardId, file, {
        tile_size: tileSize,
        overlap: overlapMargin,
        conf_threshold: confThreshold,
        iou_threshold: iouThreshold,
      }),
    onSuccess: (data) => {
      setActiveInspectionId(data.id);
    },
  });

  const onDrop = useCallback(
    (files: File[]) => {
      if (files[0]) uploadMutation.mutate(files[0]);
    },
    [uploadMutation, boardId, tileSize, overlapMargin, confThreshold, iouThreshold]
  );

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { "image/*": [".png", ".jpg", ".jpeg", ".bmp"] },
    multiple: false,
  });

  const defects = inspection?.defects ?? [];
  const classCounts: Record<string, number> = {};
  const severityCounts: Record<string, number> = { CRITICAL: 0, MAJOR: 0, MINOR: 0 };
  for (const d of defects) {
    classCounts[d.class] = (classCounts[d.class] ?? 0) + 1;
    severityCounts[d.iso_severity] = (severityCounts[d.iso_severity] ?? 0) + 1;
  }
  const barData = Object.entries(classCounts).map(([k, v]) => ({ name: k, count: v, fill: defectColors[k as DefectClass] }));
  const pieData = Object.entries(severityCounts)
    .filter(([, v]) => v > 0)
    .map(([k, v]) => ({ name: k, value: v, fill: severityColors[k as Severity] }));

  const slaMs = 10000;
  const cycleMs = inspection?.cycle_time_ms ?? 0;
  const withinSla = cycleMs > 0 && cycleMs <= slaMs;

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      <div className="col-span-2 flex flex-col gap-4">
        <PanelCard title="Upload &amp; Live Scan">
          <div className="flex flex-col gap-3">
            <label className="flex items-center gap-2 text-xs font-mono uppercase text-text-secondary">
              Board ID
              <input className="visi-input" value={boardId} onChange={(e) => setBoardId(e.target.value)} />
            </label>
            <div
              {...getRootProps()}
              className={`border-2 border-dashed rounded-industrial p-6 text-center cursor-pointer font-mono text-xs uppercase tracking-wider ${
                isDragActive ? "border-accent-cyan text-accent-cyan" : "border-border text-text-secondary"
              }`}
            >
              <input {...getInputProps()} />
              {uploadMutation.isPending ? "Uploading..." : "Drop a PCB image here, or click to select (up to 4096x4096px)"}
            </div>
            {uploadMutation.isError && (
              <div className="text-accent-crimson text-xs font-mono">
                {(uploadMutation.error as any)?.response?.data?.detail ?? "Upload failed."}
              </div>
            )}
            <TerminalLog entries={log} />
            <div className="text-[10px] font-mono text-text-muted">
              WS: {connected ? "connected" : "disconnected"} {activeInspectionId ? `· inspection #${activeInspectionId}` : ""}
            </div>
          </div>
        </PanelCard>

        <PanelCard title="Annotated Viewport">
          {inspection && inspection.status === "COMPLETE" ? (
            <div className="flex flex-col gap-3">
              <ZoomControls />
              <TileGridOverlay
                path={`/api/v1/inspections/${inspection.id}/image?grid=${showTileGrid}`}
                zoom={zoom}
                offsetX={offsetX}
                offsetY={offsetY}
              />
            </div>
          ) : (
            <div className="text-text-muted text-sm">Upload a board image to see live tiling + detections.</div>
          )}
        </PanelCard>
      </div>

      <div className="flex flex-col gap-4">
        <PanelCard title="Inspection Summary">
          {inspection ? (
            <div className="flex flex-col gap-2 text-sm">
              <Metric label="Total Anomalies" value={defects.length} />
              <Metric label="Critical" value={severityCounts.CRITICAL} valueColor={severityColors.CRITICAL} />
              <Metric label="Major" value={severityCounts.MAJOR} valueColor={severityColors.MAJOR} />
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs uppercase text-text-secondary">Disposition</span>
                <SeverityBadge severity={inspection.board_disposition === "NONCONFORMING" ? "CRITICAL" : "MINOR"} />
              </div>
              <div className="flex items-center justify-between">
                <span className="font-mono text-xs uppercase text-text-secondary">Status</span>
                <span className="font-code text-xs">{inspection.status}</span>
              </div>
            </div>
          ) : (
            <div className="text-text-muted text-sm">No inspection yet.</div>
          )}
        </PanelCard>

        <PanelCard title="Defects by Class">
          <ResponsiveContainer width="100%" height={160}>
            <BarChart data={barData}>
              <XAxis dataKey="name" tick={{ fontSize: 10, fill: "#8896A8" }} />
              <YAxis allowDecimals={false} tick={{ fontSize: 10, fill: "#8896A8" }} />
              <Tooltip contentStyle={{ background: "#1A1F26", border: "1px solid #252C36" }} />
              <Bar dataKey="count">
                {barData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </PanelCard>

        <PanelCard title="Severity Mix">
          <ResponsiveContainer width="100%" height={160}>
            <PieChart>
              <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={35} outerRadius={60}>
                {pieData.map((entry, i) => (
                  <Cell key={i} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip contentStyle={{ background: "#1A1F26", border: "1px solid #252C36" }} />
            </PieChart>
          </ResponsiveContainer>
        </PanelCard>

        <PanelCard title="Cycle Time vs SLA">
          <div className="flex flex-col gap-1">
            <div className="font-code text-2xl" style={{ color: withinSla ? severityColors.MINOR : severityColors.CRITICAL }}>
              {cycleMs} ms
            </div>
            <div className="text-[10px] font-mono uppercase text-text-secondary">Target SLA: &lt; {slaMs} ms / board</div>
          </div>
        </PanelCard>
      </div>
    </div>
  );
}

function Metric({ label, value, valueColor }: { label: string; value: number; valueColor?: string }) {
  return (
    <div className="flex items-center justify-between">
      <span className="font-mono text-xs uppercase text-text-secondary">{label}</span>
      <span className="font-code text-lg" style={{ color: valueColor }}>
        {value}
      </span>
    </div>
  );
}
