from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.security import get_current_user
from app.models.audit_log import AuditLog
from app.models.defect import Defect
from app.models.user import User
from app.schemas.api import DefectPatch

router = APIRouter(prefix="/defects", tags=["defects"])


@router.patch("/{defect_id}")
async def patch_defect(
    defect_id: str,
    body: DefectPatch,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    result = await db.execute(select(Defect).where(Defect.defect_id == defect_id))
    defect = result.scalar_one_or_none()
    if defect is None:
        raise HTTPException(status_code=404, detail="Defect not found")

    previous_status = defect.status
    defect.status = body.status
    defect.engineer_notes = body.engineer_notes
    defect.validated_by = user.id
    defect.validated_at = datetime.now(timezone.utc)

    db.add(
        AuditLog(
            inspection_id=defect.inspection_id,
            actor=user.id,
            action=f"DEFECT_{body.status}",
            defect_id=defect.defect_id,
            detail=f"Status changed {previous_status} -> {body.status}."
            + (f" Notes: {body.engineer_notes}" if body.engineer_notes else ""),
        )
    )
    await db.commit()
    await db.refresh(defect)
    return {
        "defect_id": defect.defect_id,
        "status": defect.status,
        "engineer_notes": defect.engineer_notes,
        "validated_by": defect.validated_by,
        "validated_at": defect.validated_at,
    }
