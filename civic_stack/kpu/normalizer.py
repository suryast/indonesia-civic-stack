"""KPU normalizer — KPU JSON API responses → CivicStackResponse."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from civic_stack.shared.schema import CivicStackResponse, RecordStatus

MODULE = "kpu"


def normalize_candidate(
    data: dict[str, Any],
    *,
    source_url: str,
    debug: bool = False,
) -> CivicStackResponse:
    result = {
        "candidate_id": str(data.get("id", data.get("no_urut", ""))),
        "name": data.get("nama", data.get("name", "")),
        "party": data.get("partai", data.get("nama_partai", "")),
        "party_no": data.get("no_partai"),
        "election_type": data.get("jenis_pemilu", data.get("election_type", "")),
        "region": data.get("dapil", data.get("wilayah", "")),
        "position": data.get("jabatan", data.get("posisi", "")),
        "gender": data.get("jenis_kelamin", data.get("gender")),
        "photo_url": data.get("foto", data.get("photo_url")),
        "vote_count": data.get("suara_sah", data.get("vote_count")),
        "elected": data.get("terpilih", data.get("elected")),
    }
    result = {k: v for k, v in result.items() if v is not None}

    status = RecordStatus.ACTIVE if result.get("name") else RecordStatus.NOT_FOUND

    return CivicStackResponse(
        result=result,
        found=bool(result.get("name")),
        status=status,
        confidence=1.0 if data.get("id") else 0.9,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
        raw=data if debug else None,
    )


def normalize_election_results(
    data: dict[str, Any],
    *,
    source_url: str,
    region_code: str,
) -> CivicStackResponse:
    # SIREKAP returns aggregate vote tallies per party/candidate
    chart = data.get("chart", {})

    result = {
        "region_code": region_code,
        "election_type": source_url.split("/hhcw/")[-1].split("/")[0],
        "total_votes": sum(chart.values()) if isinstance(chart, dict) else None,
        "results_by_party": chart,
        "tps_reported": data.get("progres", {}).get("total"),
        "tps_total": data.get("progres", {}).get("progres"),
        "last_updated": data.get("ts"),
    }

    return CivicStackResponse(
        result={k: v for k, v in result.items() if v is not None},
        found=bool(chart),
        status=RecordStatus.ACTIVE if chart else RecordStatus.NOT_FOUND,
        confidence=1.0,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
    )


def normalize_finance(
    data: dict[str, Any],
    *,
    source_url: str,
) -> CivicStackResponse:
    result = {
        "candidate_id": str(data.get("id_caleg", "")),
        "candidate_name": data.get("nama_caleg", ""),
        "initial_balance_idr": data.get("saldo_awal"),
        "total_income_idr": data.get("total_penerimaan"),
        "total_expenditure_idr": data.get("total_pengeluaran"),
        "reporting_period": data.get("periode"),
        "report_status": data.get("status_laporan"),
    }

    return CivicStackResponse(
        result={k: v for k, v in result.items() if v is not None},
        found=bool(result.get("candidate_name")),
        status=RecordStatus.ACTIVE,
        confidence=1.0,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=MODULE,
    )
