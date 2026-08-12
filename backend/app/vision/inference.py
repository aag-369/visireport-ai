"""Real YOLO inference: loads the shipped Ultralytics weights and runs a
genuine forward pass on each image tile. No random/mocked detections are
ever produced here - if the weights file is missing or fails to load,
`ModelNotAvailableError` is raised and the API surfaces a 503, per spec."""
import logging
import threading
import time
from pathlib import Path

from app.config import get_settings
from app.vision.tiling import (
    GlobalDetection,
    RawDetection,
    compute_tiles,
    merge_detections,
    remap_to_global,
)

logger = logging.getLogger("visireport.vision")

CLASS_NAMES = ["open", "short", "mousebite", "spur", "copper", "pin-hole"]


class ModelNotAvailableError(RuntimeError):
    pass


class YoloEngine:
    """Thread-safe lazy-loaded singleton wrapper around an Ultralytics YOLO model."""

    _instance: "YoloEngine | None" = None
    _lock = threading.Lock()

    def __init__(self):
        self._model = None
        self._load_error: str | None = None
        self._weights_path: str | None = None

    @classmethod
    def instance(cls) -> "YoloEngine":
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def load(self, force: bool = False):
        settings = get_settings()
        if self._model is not None and not force:
            return
        weights_path = Path(settings.model_weights_path)
        if not weights_path.exists():
            self._load_error = f"Model weights not found at {weights_path}"
            self._model = None
            logger.warning(self._load_error)
            return
        try:
            from ultralytics import YOLO  # imported lazily - heavy dependency

            self._model = YOLO(str(weights_path))
            self._weights_path = str(weights_path)
            self._load_error = None
            logger.info("Loaded YOLO weights from %s", weights_path)
        except Exception as exc:  # pragma: no cover - defensive
            self._load_error = f"Failed to load model: {exc}"
            self._model = None
            logger.exception("YOLO load failure")

    @property
    def is_ready(self) -> bool:
        return self._model is not None

    @property
    def status(self) -> dict:
        return {
            "ready": self.is_ready,
            "weights_path": self._weights_path,
            "error": self._load_error,
        }

    def predict_tile(self, image, conf_threshold: float, iou_threshold: float) -> list[RawDetection]:
        if self._model is None:
            raise ModelNotAvailableError(self._load_error or "Model not loaded")

        results = self._model.predict(
            source=image,
            conf=conf_threshold,
            iou=iou_threshold,
            verbose=False,
        )
        detections: list[RawDetection] = []
        for r in results:
            names = r.names
            for box in r.boxes:
                cls_id = int(box.cls[0])
                cls_name = names.get(cls_id, str(cls_id)) if isinstance(names, dict) else names[cls_id]
                conf = float(box.conf[0])
                x1, y1, x2, y2 = (int(v) for v in box.xyxy[0].tolist())
                detections.append(
                    RawDetection(cls=cls_name, confidence=conf, x=x1, y=y1, w=x2 - x1, h=y2 - y1)
                )
        return detections


def run_tiled_inference(
    image,
    tile_size: int,
    overlap: int,
    conf_threshold: float,
    iou_threshold: float,
    progress_cb=None,
) -> tuple[list[GlobalDetection], list[dict], int]:
    """Slice `image` (a numpy BGR array) into tiles, run real inference on
    each, remap + merge, and return (merged_detections, tile_stats,
    cycle_time_ms). `progress_cb(event: dict)` is invoked per tile for
    live progress streaming over the WebSocket."""
    engine = YoloEngine.instance()
    engine.load()
    if not engine.is_ready:
        raise ModelNotAvailableError(engine.status["error"] or "Model not available")

    start = time.monotonic()
    img_h, img_w = image.shape[:2]
    tiles = compute_tiles(img_w, img_h, tile_size, overlap)

    all_global: list[GlobalDetection] = []
    tile_stats = []
    for idx, tile in enumerate(tiles):
        tile_img = image[tile.y0:tile.y1, tile.x0:tile.x1]
        raw = engine.predict_tile(tile_img, conf_threshold, iou_threshold)
        global_dets = remap_to_global(tile, raw)
        all_global.extend(global_dets)
        tile_stats.append(
            {
                "tile_index": idx,
                "row": tile.row,
                "col": tile.col,
                "x0": tile.x0,
                "y0": tile.y0,
                "x1": tile.x1,
                "y1": tile.y1,
                "detection_count": len(raw),
            }
        )
        if progress_cb:
            progress_cb(
                {
                    "event": "tile_processed",
                    "tile_index": idx,
                    "tile_total": len(tiles),
                    "row": tile.row,
                    "col": tile.col,
                    "detections_in_tile": len(raw),
                }
            )

    merged = merge_detections(all_global, iou_threshold=iou_threshold)
    cycle_time_ms = int((time.monotonic() - start) * 1000)
    return merged, tile_stats, cycle_time_ms
