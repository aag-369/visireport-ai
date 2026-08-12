"""The VISIREPORT_SCHEMA JSON Schema (Section 6.1) enforced server-side on
every inspection payload before it is persisted or published to RabbitMQ."""

VISIREPORT_SCHEMA = {
    "type": "object",
    "required": ["report_id", "board_id", "inspection_timestamp", "defects", "board_disposition"],
    "properties": {
        "report_id": {"type": "string"},
        "board_id": {"type": "string"},
        "inspection_timestamp": {"type": "string", "format": "date-time"},
        "defects": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["defect_id", "class", "confidence", "global_bbox", "iso_severity", "status"],
                "properties": {
                    "defect_id": {"type": "string"},
                    "class": {
                        "type": "string",
                        "enum": ["open", "short", "mousebite", "spur", "copper", "pin-hole", "missing-hole"],
                    },
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "global_bbox": {
                        "type": "object",
                        "required": ["x", "y", "w", "h"],
                        "properties": {
                            "x": {"type": "integer"},
                            "y": {"type": "integer"},
                            "w": {"type": "integer"},
                            "h": {"type": "integer"},
                        },
                    },
                    "iso_severity": {"type": "string", "enum": ["CRITICAL", "MAJOR", "MINOR"]},
                    "tile_origin": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "minItems": 2,
                        "maxItems": 2,
                    },
                    "status": {"type": "string", "enum": ["PENDING", "CONFIRMED", "OVERRIDDEN"]},
                },
            },
        },
        "board_disposition": {"type": "string", "enum": ["CONFORMING", "NONCONFORMING"]},
    },
}

# Defect taxonomy: class key -> (display name, default ISO severity)
# 7 classes: the original 6 come from the DeepPCB dataset; "missing-hole" was
# added when the user's own PKU-Market-PCB dataset was incorporated (see
# backend/data/prepare_combined_dataset.py) - it is a genuinely distinct
# defect from "pin-hole" (an absent drilled hole vs. a pit/void in copper),
# so it was added as a 7th class rather than merged into an existing one.
DEFECT_TAXONOMY = {
    "open": ("Open Circuit", "CRITICAL"),
    "short": ("Short Circuit", "CRITICAL"),
    "mousebite": ("Mousebite", "MAJOR"),
    "spur": ("Spur", "MAJOR"),
    "copper": ("Spurious Copper", "MINOR"),
    "pin-hole": ("Pin-hole", "MAJOR"),
    "missing-hole": ("Missing Hole", "CRITICAL"),
}
