"""
Bootstrap tests for shared/schema.py.

These verify the Sprint 0 done condition:
  "CivicStackResponse is importable from shared.schema and pytest passes."
"""

from datetime import datetime

import pytest

from shared.schema import (
    CivicStackResponse,
    RecordStatus,
    error_response,
    not_found_response,
)


def test_response_envelope_construction():
    resp = CivicStackResponse(
        result={"id": "MD001", "name": "Test Product"},
        found=True,
        status=RecordStatus.ACTIVE,
        confidence=1.0,
        source_url="https://cekbpom.pom.go.id",
        fetched_at=datetime.utcnow(),
        module="bpom",
    )
    assert resp.found is True
    assert resp.status == RecordStatus.ACTIVE
    assert resp.confidence == 1.0
    assert resp.raw is None


def test_not_found_response():
    resp = not_found_response("bpom", "https://cekbpom.pom.go.id")
    assert resp.found is False
    assert resp.status == RecordStatus.NOT_FOUND
    assert resp.confidence == 1.0
    assert resp.result is None
    assert resp.module == "bpom"


def test_error_response():
    resp = error_response("ahu", "https://ahu.go.id", detail="Portal timeout")
    assert resp.found is False
    assert resp.status == RecordStatus.ERROR
    assert resp.confidence == 0.0
    assert resp.result == {"detail": "Portal timeout"}


def test_error_response_no_detail():
    resp = error_response("bpjph", "https://sertifikasi.halal.go.id")
    assert resp.result is None


def test_confidence_bounds():
    with pytest.raises(Exception):  # noqa: B017
        CivicStackResponse(
            found=False,
            status=RecordStatus.NOT_FOUND,
            confidence=1.5,  # out of range
            source_url="https://example.go.id",
            fetched_at=datetime.utcnow(),
            module="test",
        )


def test_json_serialization_roundtrip():
    resp = not_found_response("kpu", "https://kpu.go.id")
    data = resp.model_dump(mode="json")
    assert data["found"] is False
    assert data["status"] == "NOT_FOUND"
    assert isinstance(data["fetched_at"], str)
