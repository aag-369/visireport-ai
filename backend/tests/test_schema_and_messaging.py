import pytest
from jsonschema import ValidationError, validate

from app.messaging.producer import BrokerUnavailableError, publish_inspection_payload
from app.schemas.visireport_schema import VISIREPORT_SCHEMA


def _valid_payload():
    return {
        "report_id": "VR-20260101-000000-ABCD",
        "board_id": "PCBA-MED-001",
        "inspection_timestamp": "2026-01-01T00:00:00+00:00",
        "board_disposition": "NONCONFORMING",
        "defects": [
            {
                "defect_id": "VR-DEF-0001",
                "class": "open",
                "confidence": 0.9,
                "global_bbox": {"x": 1, "y": 2, "w": 3, "h": 4},
                "iso_severity": "CRITICAL",
                "tile_origin": [0, 0],
                "status": "PENDING",
            }
        ],
    }


def test_valid_payload_passes_schema():
    validate(instance=_valid_payload(), schema=VISIREPORT_SCHEMA)  # should not raise


def test_invalid_defect_class_fails_schema():
    payload = _valid_payload()
    payload["defects"][0]["class"] = "not-a-real-defect-class"
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=VISIREPORT_SCHEMA)


def test_missing_required_field_fails_schema():
    payload = _valid_payload()
    del payload["board_disposition"]
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=VISIREPORT_SCHEMA)


def test_confidence_out_of_range_fails_schema():
    payload = _valid_payload()
    payload["defects"][0]["confidence"] = 1.5
    with pytest.raises(ValidationError):
        validate(instance=payload, schema=VISIREPORT_SCHEMA)


@pytest.mark.asyncio
async def test_publish_fails_loudly_when_broker_unreachable():
    # conftest.py points RABBITMQ_URL at an unreachable port - the publish
    # step must raise, never silently report a fake "SIMULATED" success.
    with pytest.raises(BrokerUnavailableError):
        await publish_inspection_payload(_valid_payload())
