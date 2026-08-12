"""Real tiling: slice a (possibly up-to-4K) image into overlapping tiles,
run a detector callback on each tile, remap detections back to global image
coordinates, and merge duplicate detections across tile boundaries with
IoU-based NMS.

This module contains no network/model code - it's pure geometry - so it is
unit-testable in isolation and reused by app.vision.inference.
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class Tile:
    x0: int
    y0: int
    x1: int
    y1: int
    row: int
    col: int


@dataclass
class RawDetection:
    """A detection in TILE-local pixel coordinates, as returned by the model."""
    cls: str
    confidence: float
    x: int
    y: int
    w: int
    h: int


@dataclass
class GlobalDetection:
    """A detection remapped into GLOBAL image pixel coordinates."""
    cls: str
    confidence: float
    x: int
    y: int
    w: int
    h: int
    tile_row: int
    tile_col: int


def compute_tiles(img_w: int, img_h: int, tile_size: int, overlap: int) -> list[Tile]:
    """Slice an img_w x img_h image into overlapping tile_size x tile_size
    tiles with `overlap` px shared between neighbours. Guarantees full
    coverage of the image even when dimensions don't divide evenly."""
    if tile_size <= 0:
        raise ValueError("tile_size must be positive")
    if overlap < 0 or overlap >= tile_size:
        raise ValueError("overlap must be >= 0 and < tile_size")

    stride = tile_size - overlap

    def starts(dim: int) -> list[int]:
        if dim <= tile_size:
            return [0]
        pts = list(range(0, dim - tile_size + 1, stride))
        if pts[-1] + tile_size < dim:
            pts.append(dim - tile_size)
        return pts

    xs = starts(img_w)
    ys = starts(img_h)

    tiles: list[Tile] = []
    for row, y0 in enumerate(ys):
        for col, x0 in enumerate(xs):
            x1 = min(x0 + tile_size, img_w)
            y1 = min(y0 + tile_size, img_h)
            tiles.append(Tile(x0=x0, y0=y0, x1=x1, y1=y1, row=row, col=col))
    return tiles


def remap_to_global(tile: Tile, detections: list[RawDetection]) -> list[GlobalDetection]:
    """Translate tile-local detection coordinates into global image space."""
    out = []
    for d in detections:
        out.append(
            GlobalDetection(
                cls=d.cls,
                confidence=d.confidence,
                x=tile.x0 + d.x,
                y=tile.y0 + d.y,
                w=d.w,
                h=d.h,
                tile_row=tile.row,
                tile_col=tile.col,
            )
        )
    return out


def _iou(a: GlobalDetection, b: GlobalDetection) -> float:
    ax2, ay2 = a.x + a.w, a.y + a.h
    bx2, by2 = b.x + b.w, b.y + b.h
    ix0, iy0 = max(a.x, b.x), max(a.y, b.y)
    ix1, iy1 = min(ax2, bx2), min(ay2, by2)
    iw, ih = max(0, ix1 - ix0), max(0, iy1 - iy0)
    inter = iw * ih
    if inter == 0:
        return 0.0
    area_a = a.w * a.h
    area_b = b.w * b.h
    union = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


def merge_detections(detections: list[GlobalDetection], iou_threshold: float = 0.45) -> list[GlobalDetection]:
    """Cross-tile-boundary de-duplication via class-wise IoU-based NMS.

    Detections straddling a tile seam are frequently reported by both
    neighbouring tiles; this collapses those duplicates into the single
    highest-confidence detection, matching real overlap-tiling pipelines.
    """
    by_class: dict[str, list[GlobalDetection]] = {}
    for d in detections:
        by_class.setdefault(d.cls, []).append(d)

    kept: list[GlobalDetection] = []
    for cls_dets in by_class.values():
        cls_dets = sorted(cls_dets, key=lambda d: d.confidence, reverse=True)
        active = list(cls_dets)
        while active:
            best = active.pop(0)
            kept.append(best)
            active = [d for d in active if _iou(best, d) < iou_threshold]
    return kept
