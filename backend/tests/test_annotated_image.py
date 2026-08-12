import cv2
import numpy as np
import pytest

from tests.test_defect_workflow import _seed_inspection_with_defect


@pytest.mark.asyncio
async def test_annotated_image_endpoint_returns_real_jpeg(client, auth_headers, tmp_path):
    inspection_id, _ = await _seed_inspection_with_defect()

    # The seeded inspection points at /tmp/fake.jpg which doesn't exist yet -
    # write a real tiny image there so cv2.imread succeeds.
    img = np.zeros((200, 200, 3), dtype=np.uint8)
    cv2.imwrite("/tmp/fake.jpg", img)

    resp = await client.get(f"/api/v1/inspections/{inspection_id}/image", headers=auth_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "image/jpeg"
    assert resp.content[:2] == b"\xff\xd8"  # real JPEG magic bytes


@pytest.mark.asyncio
async def test_annotated_image_requires_auth(client):
    resp = await client.get("/api/v1/inspections/1/image")
    assert resp.status_code == 401
