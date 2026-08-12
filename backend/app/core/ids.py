import secrets
from datetime import datetime, timezone


def new_report_id() -> str:
    now = datetime.now(timezone.utc)
    return f"VR-{now.strftime('%Y%m%d-%H%M%S')}-{secrets.token_hex(2).upper()}"


def new_board_id(seq: int) -> str:
    return f"PCBA-MED-{seq:03d}"


def new_defect_id(seq: int) -> str:
    return f"VR-DEF-{seq:04d}"
