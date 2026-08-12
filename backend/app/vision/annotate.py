"""OpenCV bbox/label drawing using the exact defect-class palette from
Section 5.1 of the theme spec, so annotated images match the frontend's
color coding."""
import cv2
import numpy as np

# BGR (OpenCV) versions of the hex tokens in Section 5.1
DEFECT_COLORS_BGR = {
    "open": (255, 121, 41),        # #2979FF
    "short": (59, 59, 255),        # #FF3B3B
    "mousebite": (199, 110, 255),  # #FF6EC7
    "spur": (32, 176, 255),        # #FFB020
    "copper": (0, 109, 255),       # #FF6D00
    "pin-hole": (118, 230, 0),     # #00E676
}


def annotate_image(image: np.ndarray, detections: list, tile_grid: list[dict] | None = None) -> np.ndarray:
    out = image.copy()
    if tile_grid:
        for t in tile_grid:
            cv2.rectangle(out, (t["x0"], t["y0"]), (t["x1"], t["y1"]), (80, 80, 80), 1)

    for d in detections:
        color = DEFECT_COLORS_BGR.get(d.cls, (232, 237, 245))
        x1, y1, x2, y2 = d.x, d.y, d.x + d.w, d.y + d.h
        cv2.rectangle(out, (x1, y1), (x2, y2), color, 2)
        label = f"{d.cls} {d.confidence:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)
        cv2.rectangle(out, (x1, max(0, y1 - th - 6)), (x1 + tw + 4, y1), color, -1)
        cv2.putText(out, label, (x1 + 2, max(12, y1 - 4)), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (10, 10, 10), 1, cv2.LINE_AA)
    return out
