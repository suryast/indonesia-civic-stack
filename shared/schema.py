"""Unified response schema for all civic-stack modules."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class ResponseStatus(StrEnum):
    """Status of a civic-stack response."""

    OK = "ok"
    NOT_FOUND = "not_found"
    ERROR = "error"
    DEGRADED = "degraded"  # partial data, source unreliable
    BLOCKED = "blocked"  # bot detection triggered


class ModuleName(StrEnum):
    """Registry of available modules."""

    BPOM = "bpom"
    BPJPH = "bpjph"
    AHU = "ahu"
    OJK = "ojk"
    OSS_NIB = "oss_nib"
    LPSE = "lpse"
    KPU = "kpu"
    LHKPN = "lhkpn"
    BPS = "bps"
    BMKG = "bmkg"
    SIMBG = "simbg"


class CivicStackResponse(BaseModel):
    """Standard envelope for all civic-stack module responses.

    Every module's fetch() and search() must return this shape.
    Consumers can rely on a stable contract regardless of which
    government portal is being queried.
    """

    result: dict[str, Any] | list[dict[str, Any]] | None = Field(
        default=None,
        description="Normalized data payload. dict for single-record, list for search results.",
    )
    found: bool = Field(
        default=False,
        description="Whether the query matched any records.",
    )
    status: ResponseStatus = Field(
        default=ResponseStatus.OK,
        description="Response status.",
    )
    confidence: float = Field(
        default=1.0,
        ge=0.0,
        le=1.0,
        description="Data confidence score. <1.0 for partial/stale/inferred results.",
    )
    source_url: str = Field(
        default="",
        description="URL of the government portal queried.",
    )
    fetched_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=__import__("datetime").timezone.utc),
        description="Timestamp of this fetch.",
    )
    last_updated: datetime | None = Field(
        default=None,
        description="Last-modified date from source, if available.",
    )
    module: ModuleName | str = Field(
        description="Which module produced this response.",
    )
    raw: dict[str, Any] | None = Field(
        default=None,
        description="Raw response from source (for debugging). Excluded in production.",
    )
    total_results: int = Field(
        default=0,
        description="Total matching records (for paginated search).",
    )
    page: int = Field(default=1, description="Current page number.")
    error_message: str | None = Field(
        default=None,
        description="Human-readable error message when status != ok.",
    )
