"""
Shared response envelope for all indonesia-civic-stack modules.

Every module's fetch() and search() must return CivicStackResponse.
This contract is what lets Kah products swap data sources without
changing application logic.
"""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class RecordStatus(StrEnum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    SUSPENDED = "SUSPENDED"
    REVOKED = "REVOKED"
    NOT_FOUND = "NOT_FOUND"
    ERROR = "ERROR"


class CivicStackResponse(BaseModel):
    """
    Normalized response envelope returned by every module.

    Consumers should key on `found` and `status` before reading `result`.
    The `raw` field is only populated when the caller passes debug=True.
    """

    result: dict[str, Any] | None = Field(
        default=None,
        description="Normalized domain object. Schema is module-specific and documented per module.",
    )
    found: bool = Field(
        description="True if a record was located for the query.",
    )
    status: RecordStatus = Field(
        description="Canonical status of the located record, or NOT_FOUND / ERROR.",
    )
    confidence: float = Field(
        ge=0.0,
        le=1.0,
        description="Scraper confidence in result accuracy. 1.0 = verified exact match.",
    )
    source_url: str = Field(
        description="The canonical government URL this data was retrieved from.",
    )
    fetched_at: datetime = Field(
        description="Timestamp of this specific fetch (UTC).",
    )
    last_updated: datetime | None = Field(
        default=None,
        description="Last known update date from the source portal, if available.",
    )
    module: str = Field(
        description="Module identifier, e.g. 'bpom', 'ahu', 'bpjph'.",
    )
    raw: dict[str, Any] | None = Field(
        default=None,
        description="Raw scraped data before normalization. Only included when debug=True.",
    )

    model_config = {"use_enum_values": True}


def not_found_response(
    module: str,
    source_url: str,
    *,
    query: str | None = None,
    extra: dict[str, Any] | None = None,
) -> CivicStackResponse:
    """Convenience constructor for a clean NOT_FOUND response."""
    result = extra if extra else None
    return CivicStackResponse(
        result=result,
        found=False,
        status=RecordStatus.NOT_FOUND,
        confidence=1.0,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=module,
    )


def error_response(
    module: str,
    source_url: str,
    *,
    query: str | None = None,
    detail: str | None = None,
    message: str | None = None,
) -> CivicStackResponse:
    """Convenience constructor for an ERROR response."""
    msg = detail or message
    result = {"detail": msg} if msg else None
    return CivicStackResponse(
        result=result,
        found=False,
        status=RecordStatus.ERROR,
        confidence=0.0,
        source_url=source_url,
        fetched_at=datetime.utcnow(),
        module=module,
    )
