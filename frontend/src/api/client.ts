import axios from "axios";
import type { AuditEntry, Inspection, ModelMetrics, Narrative, SystemStatus } from "./types";

export const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
export const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? "ws://localhost:8000";

const http = axios.create({ baseURL: API_BASE_URL });

http.interceptors.request.use((config) => {
  const token = localStorageSafe.get("visireport_token");
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Wrapped in try/catch so JWT persistence degrades gracefully in
// environments where localStorage is unavailable or blocked (private
// browsing, restrictive browser settings, etc).
const localStorageSafe = {
  get(key: string): string | null {
    try {
      return window.localStorage.getItem(key);
    } catch {
      return null;
    }
  },
  set(key: string, value: string) {
    try {
      window.localStorage.setItem(key, value);
    } catch {
      /* ignore */
    }
  },
  clear(key: string) {
    try {
      window.localStorage.removeItem(key);
    } catch {
      /* ignore */
    }
  },
};

export const tokenStorage = localStorageSafe;

export const api = {
  async login(email: string, password: string) {
    const { data } = await http.post("/api/v1/auth/login", { email, password });
    return data as { access_token: string; role: string; name: string };
  },
  async health() {
    const { data } = await http.get("/api/v1/health");
    return data;
  },
  async createBoard(board_id?: string) {
    const { data } = await http.post("/api/v1/boards", { board_id });
    return data;
  },
  async uploadInspection(
    boardId: string,
    file: File,
    params: { tile_size: number; overlap: number; conf_threshold: number; iou_threshold: number }
  ) {
    const form = new FormData();
    form.append("file", file);
    const { data } = await http.post<Inspection>(
      `/api/v1/boards/${boardId}/inspections`,
      form,
      {
        headers: { "Content-Type": "multipart/form-data" },
        params,
      }
    );
    return data;
  },
  async getInspection(id: number) {
    const { data } = await http.get<Inspection>(`/api/v1/inspections/${id}`);
    return data;
  },
  async getDefects(id: number, filters: Record<string, string | number | undefined> = {}) {
    const { data } = await http.get(`/api/v1/inspections/${id}/defects`, { params: filters });
    return data as { count: number; defects: Inspection["defects"] };
  },
  async patchDefect(defectId: string, body: { status: string; engineer_notes?: string }) {
    const { data } = await http.patch(`/api/v1/defects/${defectId}`, body);
    return data;
  },
  async getNarrative(id: number) {
    const { data } = await http.get<Narrative>(`/api/v1/inspections/${id}/narrative`);
    return data;
  },
  async regenerateNarrative(id: number) {
    const { data } = await http.post<Narrative>(`/api/v1/inspections/${id}/narrative/regenerate`);
    return data;
  },
  reportPdfUrl(id: number) {
    return `${API_BASE_URL}/api/v1/inspections/${id}/report.pdf`;
  },
  async getAuditLog(params: Record<string, string | number | undefined> = {}) {
    const { data } = await http.get("/api/v1/audit-log", { params });
    return data as { entries: AuditEntry[]; page: number; page_size: number };
  },
  auditCsvUrl() {
    return `${API_BASE_URL}/api/v1/audit-log/export.csv`;
  },
  async getModelMetrics() {
    const { data } = await http.get<ModelMetrics>("/api/v1/model/metrics");
    return data;
  },
  async getSystemStatus() {
    const { data } = await http.get<SystemStatus>("/api/v1/system/status");
    return data;
  },
};

export default http;
