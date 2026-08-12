"""Pure unit tests for the real tiling/remap/merge math - no model, no I/O."""
from app.vision.tiling import (
    GlobalDetection,
    RawDetection,
    compute_tiles,
    merge_detections,
    remap_to_global,
)


def test_compute_tiles_covers_full_image_with_overlap():
    tiles = compute_tiles(img_w=1000, img_h=1000, tile_size=400, overlap=50)
    assert len(tiles) > 1
    # Every pixel column must be covered by at least one tile.
    covered = set()
    for t in tiles:
        covered.update(range(t.x0, t.x1))
    assert covered == set(range(1000))


def test_compute_tiles_small_image_single_tile():
    tiles = compute_tiles(img_w=300, img_h=300, tile_size=640, overlap=64)
    assert len(tiles) == 1
    assert tiles[0].x0 == 0 and tiles[0].y0 == 0


def test_compute_tiles_4k_image_produces_grid():
    tiles = compute_tiles(img_w=4096, img_h=4096, tile_size=640, overlap=64)
    rows = {t.row for t in tiles}
    cols = {t.col for t in tiles}
    assert len(rows) > 5 and len(cols) > 5


def test_remap_translates_tile_local_to_global():
    from app.vision.tiling import Tile

    tile = Tile(x0=500, y0=300, x1=1140, y1=940, row=0, col=1)
    raw = [RawDetection(cls="open", confidence=0.9, x=10, y=20, w=30, h=40)]
    remapped = remap_to_global(tile, raw)
    assert remapped[0].x == 510
    assert remapped[0].y == 320
    assert remapped[0].tile_col == 1


def test_merge_deduplicates_boundary_straddling_detection():
    # Same physical defect detected by two neighbouring tiles with near-identical bboxes.
    a = GlobalDetection(cls="short", confidence=0.92, x=100, y=100, w=40, h=40, tile_row=0, tile_col=0)
    b = GlobalDetection(cls="short", confidence=0.81, x=104, y=102, w=40, h=40, tile_row=0, tile_col=1)
    merged = merge_detections([a, b], iou_threshold=0.45)
    assert len(merged) == 1
    assert merged[0].confidence == 0.92  # keeps the higher-confidence detection


def test_merge_keeps_distinct_detections():
    a = GlobalDetection(cls="open", confidence=0.9, x=0, y=0, w=20, h=20, tile_row=0, tile_col=0)
    b = GlobalDetection(cls="open", confidence=0.9, x=500, y=500, w=20, h=20, tile_row=1, tile_col=1)
    merged = merge_detections([a, b], iou_threshold=0.45)
    assert len(merged) == 2


def test_merge_does_not_collapse_different_classes():
    a = GlobalDetection(cls="open", confidence=0.9, x=100, y=100, w=40, h=40, tile_row=0, tile_col=0)
    b = GlobalDetection(cls="short", confidence=0.9, x=100, y=100, w=40, h=40, tile_row=0, tile_col=0)
    merged = merge_detections([a, b], iou_threshold=0.45)
    assert len(merged) == 2
