import { useEffect, useRef, useState } from "react";
import { WS_BASE_URL } from "../api/client";

export interface ScanLogEntry {
  timestamp: string;
  message: string;
  level: "info" | "success" | "warn" | "error";
}

/**
 * Connects to the real backend WebSocket at /ws/inspections/{id} and turns
 * each real progress event (tile processed, schema validated, queue
 * dispatched, narrative ready/failed) into a scan-log line and a raw event
 * for consumers that need structured data (e.g. tile-grid overlay counts).
 */
export function useInspectionSocket(inspectionId: number | null) {
  const [log, setLog] = useState<ScanLogEntry[]>([]);
  const [lastEvent, setLastEvent] = useState<Record<string, unknown> | null>(null);
  const [connected, setConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  useEffect(() => {
    if (inspectionId == null) return;
    const ws = new WebSocket(`${WS_BASE_URL}/ws/inspections/${inspectionId}`);
    wsRef.current = ws;

    ws.onopen = () => {
      setConnected(true);
      pushLog(`WebSocket connected to /ws/inspections/${inspectionId}`, "info");
    };
    ws.onclose = () => setConnected(false);
    ws.onerror = () => pushLog("WebSocket error", "error");

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        setLastEvent(data);
        pushLog(describeEvent(data), levelForEvent(data));
      } catch {
        pushLog(`Unparsed message: ${evt.data}`, "warn");
      }
    };

    function pushLog(message: string, level: ScanLogEntry["level"]) {
      const ts = new Date();
      const stamp = `${String(ts.getHours()).padStart(2, "0")}:${String(ts.getMinutes()).padStart(2, "0")}.${String(
        ts.getMilliseconds()
      ).padStart(3, "0")}`;
      setLog((prev) => [...prev, { timestamp: stamp, message, level }].slice(-500));
    }

    return () => {
      ws.close();
      wsRef.current = null;
    };
  }, [inspectionId]);

  return { log, lastEvent, connected, clear: () => setLog([]) };
}

function describeEvent(data: Record<string, unknown>): string {
  switch (data.event) {
    case "tile_processed":
      return `TILE ${Number(data.tile_index) + 1}/${data.tile_total} [row=${data.row} col=${data.col}] -> ${
        data.detections_in_tile
      } detection(s)`;
    case "inference_complete":
      return `INFERENCE COMPLETE - ${data.defect_count} defect(s) merged across ${data.tile_count} tile(s)`;
    case "queue_dispatched":
      return "SCHEMA VALID - payload dispatched to RabbitMQ exchange";
    case "queue_dispatch_failed":
      return `QUEUE DISPATCH FAILED - ${data.detail}`;
    case "narrative_ready":
      return "LLM SYNTHESIS COMPLETE - NCR narrative ready";
    case "narrative_failed":
      return `LLM SYNTHESIS FAILED - ${data.detail}`;
    case "inspection_failed":
      return `INSPECTION FAILED - ${data.detail}`;
    default:
      return JSON.stringify(data);
  }
}

function levelForEvent(data: Record<string, unknown>): ScanLogEntry["level"] {
  const evt = String(data.event ?? "");
  if (evt.includes("failed")) return "error";
  if (evt.includes("complete") || evt.includes("ready") || evt === "queue_dispatched") return "success";
  return "info";
}
