"""Builds a VISIREPORT_SCHEMA-shaped dict from ORM objects, for schema
validation, RabbitMQ publishing, PDF generation, and API responses - a
single source of truth so all four stay in sync."""
from app.models.defect import Defect
from app.models.inspection import Inspection


def build_inspection_payload(inspection: Inspection, defects: list[Defect]) -> dict:
    return {
        "report_id": inspection.report_id,
        "board_id": inspection.board.board_id if inspection.board else None,
        "inspection_timestamp": inspection.inspection_timestamp.isoformat(),
        "board_disposition": inspection.board_disposition,
        "defects": [
            {
                "defect_id": d.defect_id,
                "class": d.defect_class,
                "confidence": d.confidence,
                "global_bbox": {"x": d.bbox_x, "y": d.bbox_y, "w": d.bbox_w, "h": d.bbox_h},
                "iso_severity": d.iso_severity,
                "tile_origin": [d.tile_origin_row, d.tile_origin_col],
                "status": d.status,
            }
            for d in defects
        ],
    }
