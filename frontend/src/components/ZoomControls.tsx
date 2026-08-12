import { useUIStore } from "../store/uiStore";

export function ZoomControls() {
  const { zoom, offsetX, offsetY, setZoom, setOffsetX, setOffsetY, showTileGrid, toggleTileGrid } = useUIStore();
  return (
    <div className="flex flex-wrap items-center gap-4 font-mono text-[11px] uppercase text-text-secondary">
      <label className="flex items-center gap-2">
        Zoom
        <input type="range" min={0.5} max={4} step={0.1} value={zoom} onChange={(e) => setZoom(Number(e.target.value))} />
        <span className="font-code text-text-primary">{zoom.toFixed(1)}x</span>
      </label>
      <label className="flex items-center gap-2">
        X Offset
        <input type="range" min={-400} max={400} step={5} value={offsetX} onChange={(e) => setOffsetX(Number(e.target.value))} />
      </label>
      <label className="flex items-center gap-2">
        Y Offset
        <input type="range" min={-400} max={400} step={5} value={offsetY} onChange={(e) => setOffsetY(Number(e.target.value))} />
      </label>
      <button className="visi-btn" onClick={toggleTileGrid} type="button">
        Tile Grid: {showTileGrid ? "On" : "Off"}
      </button>
    </div>
  );
}
