"""Test shared schema and response envelope."""

from datetime import datetime

from shared.schema import CivicStackResponse, ModuleName, ResponseStatus


def test_civic_stack_response_defaults():
    """CivicStackResponse should have sensible defaults."""
    resp = CivicStackResponse(module=ModuleName.BPOM)
    assert resp.found is False
    assert resp.status == ResponseStatus.OK
    assert resp.confidence == 1.0
    assert resp.module == "bpom"
    assert resp.result is None
    assert isinstance(resp.fetched_at, datetime)


def test_civic_stack_response_with_data():
    """CivicStackResponse should accept a result dict."""
    resp = CivicStackResponse(
        module=ModuleName.BPJPH,
        found=True,
        result={"cert_no": "BPJPH-12345", "company": "PT Contoh"},
        source_url="https://sertifikasi.halal.go.id",
        confidence=0.95,
    )
    assert resp.found is True
    assert resp.result["cert_no"] == "BPJPH-12345"
    assert resp.confidence == 0.95


def test_civic_stack_response_search():
    """CivicStackResponse should accept a list of results."""
    resp = CivicStackResponse(
        module=ModuleName.BPOM,
        found=True,
        result=[
            {"name": "Mie Goreng A", "status": "ACTIVE"},
            {"name": "Mie Goreng B", "status": "EXPIRED"},
        ],
        total_results=42,
        page=1,
    )
    assert isinstance(resp.result, list)
    assert len(resp.result) == 2
    assert resp.total_results == 42


def test_response_status_enum():
    """ResponseStatus should have expected values."""
    assert ResponseStatus.OK == "ok"
    assert ResponseStatus.NOT_FOUND == "not_found"
    assert ResponseStatus.DEGRADED == "degraded"
    assert ResponseStatus.BLOCKED == "blocked"


def test_module_name_enum():
    """ModuleName should include all Phase 1-3 modules."""
    assert ModuleName.BPOM == "bpom"
    assert ModuleName.BPJPH == "bpjph"
    assert ModuleName.AHU == "ahu"
    assert ModuleName.OJK == "ojk"
    assert ModuleName.KPU == "kpu"


def test_civic_stack_response_serialization():
    """CivicStackResponse should serialize to JSON cleanly."""
    resp = CivicStackResponse(
        module=ModuleName.AHU,
        found=True,
        result={"company": "PT Test", "status": "ACTIVE"},
        error_message=None,
    )
    data = resp.model_dump(mode="json", exclude_none=True)
    assert "error_message" not in data
    assert data["module"] == "ahu"
    assert data["found"] is True
