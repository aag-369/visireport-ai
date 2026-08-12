import csv
import io

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.user import User

router = APIRouter(prefix="/audit-log", tags=["audit"])


async def _query_audit(
    db: AsyncSession,
    inspection_id: int | None,
    board_id: str | None,
    page: int,
    page_size: int,
):
    query = select(AuditLog).order_by(AuditLog.timestamp.desc())
    if inspection_id is not None:
        query = query.where(AuditLog.inspection_id == inspection_id)
    query = query.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(query)
    return result.scalars().all()


@router.get("")
async def list_audit_log(
    inspection_id: int | None = None,
    board_id: str | None = None,
    page: int = 1,
    page_size: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    from app.models.user import User as UserModel

    entries = await _query_audit(db, inspection_id, board_id, page, page_size)
    user_ids = {e.actor for e in entries if e.actor is not None}
    users_by_id = {}
    if user_ids:
        result = await db.execute(select(UserModel).where(UserModel.id.in_(user_ids)))
        users_by_id = {u.id: u.name for u in result.scalars().all()}

    return {
        "page": page,
        "page_size": page_size,
        "entries": [
            {
                "id": e.id,
                "inspection_id": e.inspection_id,
                "actor": e.actor,
                "actor_name": users_by_id.get(e.actor),
                "action": e.action,
                "defect_id": e.defect_id,
                "timestamp": e.timestamp,
                "detail": e.detail,
            }
            for e in entries
        ],
    }


@router.get("/export.csv")
async def export_audit_csv(
    inspection_id: int | None = None,
    board_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    entries = await _query_audit(db, inspection_id, board_id, 1, 10000)

    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["id", "inspection_id", "actor", "action", "defect_id", "timestamp", "detail"])
    for e in entries:
        writer.writerow([e.id, e.inspection_id, e.actor, e.action, e.defect_id, e.timestamp.isoformat(), e.detail])
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_log.csv"},
    )
