from __future__ import annotations

from datetime import datetime, timezone
from typing import List, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    item_id: str = "N/A"
    name: str = "N/A"
    source_type: str = "unknown"
    score: Optional[float] = None
    excerpt: str = ""


class UploadedInput(BaseModel):
    original_filename: str
    stored_path: str
    normalized_text: str
    file_type: str
    size_bytes: int


class AnalysisResult(BaseModel):
    analysis_id: str
    original_filename: str
    source_path: str
    file_type: str
    mode: str
    context: str = ""
    priority: str = "medium"
    status: str = "completed"
    error: Optional[str] = None
    executive_summary: str = ""
    most_likely_pattern_id: str = "N/A"
    predicted_next_step: str = ""
    immediate_actions: List[str] = Field(default_factory=list)
    raw_conclusion: str = ""
    evidence: List[Evidence] = Field(default_factory=list)
    created_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
