import { create } from "zustand";
import { persist } from "zustand/middleware";

interface UIState {
  activeInspectionId: number | null;
  setActiveInspectionId: (id: number | null) => void;
  selectedDefectId: string | null;
  setSelectedDefectId: (id: string | null) => void;
  zoom: number;
  offsetX: number;
  offsetY: number;
  setZoom: (z: number) => void;
  setOffsetX: (x: number) => void;
  setOffsetY: (y: number) => void;
  showTileGrid: boolean;
  toggleTileGrid: () => void;
  confThreshold: number;
  iouThreshold: number;
  tileSize: number;
  overlapMargin: number;
  setConfThreshold: (v: number) => void;
  setIouThreshold: (v: number) => void;
  setTileSize: (v: number) => void;
  setOverlapMargin: (v: number) => void;
  defectFilter: { defectClass?: string; status?: string; search?: string };
  setDefectFilter: (f: Partial<UIState["defectFilter"]>) => void;
}

export const useUIStore = create<UIState>()(
  persist(
    (set) => ({
  activeInspectionId: null,
  setActiveInspectionId: (id) => set({ activeInspectionId: id }),
  selectedDefectId: null,
  setSelectedDefectId: (id) => set({ selectedDefectId: id }),
  zoom: 1,
  offsetX: 0,
  offsetY: 0,
  setZoom: (zoom) => set({ zoom }),
  setOffsetX: (offsetX) => set({ offsetX }),
  setOffsetY: (offsetY) => set({ offsetY }),
  showTileGrid: true,
  toggleTileGrid: () => set((s) => ({ showTileGrid: !s.showTileGrid })),
  confThreshold: 0.25,
  iouThreshold: 0.45,
  tileSize: 640,
  overlapMargin: 64,
  setConfThreshold: (confThreshold) => set({ confThreshold }),
  setIouThreshold: (iouThreshold) => set({ iouThreshold }),
  setTileSize: (tileSize) => set({ tileSize }),
  setOverlapMargin: (overlapMargin) => set({ overlapMargin }),
  defectFilter: {},
  setDefectFilter: (f) => set((s) => ({ defectFilter: { ...s.defectFilter, ...f } })),
    }),
    {
      name: "visireport-ui-state",
      partialize: (s) => ({ activeInspectionId: s.activeInspectionId }),
    }
  )
);

interface AuthState {
  token: string | null;
  name: string | null;
  role: string | null;
  setAuth: (token: string, name: string, role: string) => void;
  logout: () => void;
}

export const useAuthStore = create<AuthState>((set) => ({
  token: null,
  name: null,
  role: null,
  setAuth: (token, name, role) => set({ token, name, role }),
  logout: () => set({ token: null, name: null, role: null }),
}));
