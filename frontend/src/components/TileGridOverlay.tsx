import { useEffect, useState } from "react";
import http from "../api/client";

/** Displays the backend's real annotated-image endpoint (server-drawn
 * bounding boxes + tile grid, from persisted detection coordinates) inside
 * a zoom/pan viewport. Fetched via the authenticated axios client (rather
 * than a bare <img src>) since every inspection endpoint requires a JWT. */
export function TileGridOverlay({
  path,
  zoom,
  offsetX,
  offsetY,
}: {
  path: string;
  zoom: number;
  offsetX: number;
  offsetY: number;
}) {
  const [objectUrl, setObjectUrl] = useState<string | null>(null);

  useEffect(() => {
    let revoked = "";
    http
      .get(path, { responseType: "blob" })
      .then((res) => {
        const url = URL.createObjectURL(res.data);
        revoked = url;
        setObjectUrl(url);
      })
      .catch(() => setObjectUrl(null));
    return () => {
      if (revoked) URL.revokeObjectURL(revoked);
    };
  }, [path]);

  return (
    <div className="overflow-hidden bg-bg-terminal rounded-industrial border border-border" style={{ height: 420 }}>
      {objectUrl ? (
        <div
          style={{
            transform: `scale(${zoom}) translate(${offsetX}px, ${offsetY}px)`,
            transformOrigin: "top left",
          }}
        >
          <img src={objectUrl} className="block max-w-none" alt="Annotated PCB inspection with defect bounding boxes" />
        </div>
      ) : (
        <div className="text-text-muted text-sm p-3">Loading annotated image...</div>
      )}
    </div>
  );
}
