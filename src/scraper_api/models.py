from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class ScrapeRequest(BaseModel):
    url: str
    selectors: dict[str, str] = Field(default_factory=dict)
    selector_type: Literal["css", "xpath"] = "css"
    follow_links: bool = False
    max_items: int = Field(default=20, ge=1, le=100)
    encoding_hint: str = "utf-8"


class BatchScrapeRequest(BaseModel):
    urls: list[str] = Field(..., min_length=1, max_length=20)
    selectors: dict[str, str] = Field(default_factory=dict)
    selector_type: Literal["css", "xpath"] = "css"
    max_items: int = Field(default=20, ge=1, le=100)
    encoding_hint: str = "utf-8"


class JobStatus(BaseModel):
    job_id: str
    status: Literal["pending", "running", "complete", "failed"]
    url: str | None = None
    scraped_at: datetime | None = None
    item_count: int = 0
    items: list[dict[str, Any]] = Field(default_factory=list)
    error: str | None = None


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
