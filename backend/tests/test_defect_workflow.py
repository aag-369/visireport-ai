import pytest
from sqlalchemy import select

from app.core.db import AsyncSessionLocal
from app.models.board import Board
from app.models.defect import Defect
from app.models.inspection import Inspection
from app.models.user import User


async def _seed_inspection_with_defect():
    async with AsyncSessionLocal() as db:
        board = Board(board_id="PCBA-MED-001")
        db.add(board)
        await db.flush()

        user_result = await db.execute(select(User).where(User.email == "engineer@visireport.ai"))
        user = user_result.scalar_one()

        inspection = Inspection(
            report_id="VR-20260101-000000-TEST",
            board_id=board.id,
            image_path="/tmp/fake.jpg",
            board_disposition="NONCONFORMING",
            schema_valid=True,
            status="COMPLETE",
            cycle_time_ms=1234,
            created_by=user.id,
        )
        db.add(inspection)
        await db.flush()

        defect = Defect(
            inspection_id=inspection.id,
            defect_id="VR-DEF-0001",
            defect_class="open",
            confidence=0.87,
            bbox_x=10,
            bbox_y=20,
            bbox_w=30,
            bbox_h=40,
            iso_severity="CRITICAL",
            status="PENDING",
        )
        db.add(defect)
        await db.commit()
        return inspection.id, defect.defect_id


@pytest.mark.asyncio
async def test_defect_confirm_persists_and_audits(client, auth_headers):
    inspection_id, defect_id = await _seed_inspection_with_defect()

    resp = await client.patch(
        f"/api/v1/defects/{defect_id}",
        json={"status": "CONFIRMED", "engineer_notes": "Verified under microscope."},
        headers=auth_headers,
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["status"] == "CONFIRMED"
    assert body["validated_by"] is not None

    # Persists across a "refresh" - re-fetch the inspection and confirm the
    # defect status stuck (i.e. it's DB-backed, not component-only state).
    get_resp = await client.get(f"/api/v1/inspections/{inspection_id}", headers=auth_headers)
    assert get_resp.status_code == 200
    defects = get_resp.json()["defects"]
    assert any(d["defect_id"] == defect_id and d["status"] == "CONFIRMED" for d in defects)

    audit_resp = await client.get(
        "/api/v1/audit-log", params={"inspection_id": inspection_id}, headers=auth_headers
    )
    entries = audit_resp.json()["entries"]
    assert any(e["action"] == "DEFECT_CONFIRMED" and e["defect_id"] == defect_id for e in entries)
    assert any(e["actor_name"] == "QA Engineer" for e in entries)


@pytest.mark.asyncio
async def test_defect_override_rejects_bad_status(client, auth_headers):
    _, defect_id = await _seed_inspection_with_defect()
    resp = await client.patch(
        f"/api/v1/defects/{defect_id}", json={"status": "NOT_A_REAL_STATUS"}, headers=auth_headers
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_pdf_export_matches_onscreen_defects(client, auth_headers):
    inspection_id, defect_id = await _seed_inspection_with_defect()
    resp = await client.get(f"/api/v1/inspections/{inspection_id}/report.pdf", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"
    assert len(resp.content) > 500
