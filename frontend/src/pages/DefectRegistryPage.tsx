import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { api } from "../api/client";
import { PanelCard } from "../components/PanelCard";
import { DefectBadge, SeverityBadge, StatusBadge } from "../components/DefectBadge";
import { useUIStore } from "../store/uiStore";
import type { Defect } from "../api/types";

export function DefectRegistryPage() {
  const { activeInspectionId, selectedDefectId, setSelectedDefectId, defectFilter, setDefectFilter } = useUIStore();
  const [notes, setNotes] = useState("");
  const qc = useQueryClient();

  const { data } = useQuery({
    queryKey: ["defects", activeInspectionId, defectFilter],
    queryFn: () =>
      api.getDefects(activeInspectionId as number, {
        defect_class: defectFilter.defectClass,
        status_filter: defectFilter.status,
        search: defectFilter.search,
      }),
    enabled: activeInspectionId != null,
  });

  const patchMutation = useMutation({
    mutationFn: (vars: { defectId: string; status: string }) =>
      api.patchDefect(vars.defectId, { status: vars.status, engineer_notes: notes || undefined }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["defects"] }),
  });

  if (activeInspectionId == null) {
    return (
      <div className="p-4">
        <PanelCard title="Defect Registry">
          <div className="text-text-muted text-sm">Run an inspection on the Inspection tab first.</div>
        </PanelCard>
      </div>
    );
  }

  const defects: Defect[] = data?.defects ?? [];
  const selected = defects.find((d) => d.defect_id === selectedDefectId) ?? defects[0];

  return (
    <div className="grid grid-cols-3 gap-4 p-4">
      <div className="col-span-2 flex flex-col gap-3">
        <PanelCard title={`Defect Registry (${defects.length})`}>
          <div className="flex gap-2 mb-3">
            <input
              className="visi-input flex-1"
              placeholder="Search defect ID..."
              onChange={(e) => setDefectFilter({ search: e.target.value })}
            />
            <select className="visi-input" onChange={(e) => setDefectFilter({ status: e.target.value || undefined })}>
              <option value="">All Statuses</option>
              <option value="PENDING">Pending</option>
              <option value="CONFIRMED">Confirmed</option>
              <option value="OVERRIDDEN">Overridden</option>
            </select>
          </div>
          <table className="w-full text-xs font-mono">
            <thead>
              <tr className="text-text-secondary uppercase text-left border-b border-border">
                <th className="py-1.5">Defect ID</th>
                <th>Class</th>
                <th>Severity</th>
                <th>Confidence</th>
                <th>Tile</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {defects.map((d) => (
                <tr
                  key={d.defect_id}
                  onClick={() => setSelectedDefectId(d.defect_id)}
                  className={`border-b border-border/50 cursor-pointer hover:bg-bg-tertiary ${
                    selected?.defect_id === d.defect_id ? "bg-bg-tertiary" : ""
                  }`}
                >
                  <td className="py-1.5">{d.defect_id}</td>
                  <td>
                    <DefectBadge defectClass={d.class} />
                  </td>
                  <td>
                    <SeverityBadge severity={d.iso_severity} />
                  </td>
                  <td>{(d.confidence * 100).toFixed(1)}%</td>
                  <td>
                    [{d.tile_origin[0]},{d.tile_origin[1]}]
                  </td>
                  <td>
                    <StatusBadge status={d.status} />
                  </td>
                </tr>
              ))}
              {defects.length === 0 && (
                <tr>
                  <td colSpan={6} className="py-4 text-center text-text-muted">
                    No defects match the current filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </PanelCard>
      </div>

      <PanelCard title="Defect Detail">
        {selected ? (
          <div className="flex flex-col gap-3 text-xs font-mono">
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">ID</span>
              <span>{selected.defect_id}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">Class</span>
              <DefectBadge defectClass={selected.class} />
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">Severity</span>
              <SeverityBadge severity={selected.iso_severity} />
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">Confidence</span>
              <span>{(selected.confidence * 100).toFixed(2)}%</span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">BBox (x,y,w,h)</span>
              <span>
                {selected.global_bbox.x},{selected.global_bbox.y},{selected.global_bbox.w},{selected.global_bbox.h}
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-text-secondary uppercase">Tile Origin</span>
              <span>
                row {selected.tile_origin[0]}, col {selected.tile_origin[1]}
              </span>
            </div>

            <textarea
              className="visi-input font-sans normal-case"
              placeholder="Engineer notes..."
              rows={3}
              defaultValue={selected.engineer_notes ?? ""}
              onChange={(e) => setNotes(e.target.value)}
            />
            <div className="flex gap-2">
              <button
                className="visi-btn visi-btn-primary flex-1"
                type="button"
                disabled={patchMutation.isPending}
                onClick={() => patchMutation.mutate({ defectId: selected.defect_id, status: "CONFIRMED" })}
              >
                Confirm
              </button>
              <button
                className="visi-btn flex-1"
                type="button"
                disabled={patchMutation.isPending}
                onClick={() => patchMutation.mutate({ defectId: selected.defect_id, status: "OVERRIDDEN" })}
              >
                Override
              </button>
            </div>
            {selected.validated_by && (
              <div className="text-text-muted">
                Last validated at {selected.validated_at ? new Date(selected.validated_at).toLocaleString() : "-"}
              </div>
            )}
          </div>
        ) : (
          <div className="text-text-muted text-sm">Select a defect from the registry.</div>
        )}
      </PanelCard>
    </div>
  );
}
