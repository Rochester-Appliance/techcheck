from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class DiagnosisRequest(BaseModel):
    tech_name: str = Field(..., min_length=1)
    job_number: str = Field(..., min_length=1)
    model_number: str = Field(..., min_length=1)
    problem_description: str = Field(..., min_length=1)


class IssueDetails(BaseModel):
    difficulty: Optional[str]
    time: Optional[str]
    explanation: Optional[str]
    parts: List[str]
    verify_steps: List[str]
    repair_steps: List[str]
    safety_warnings: List[str]
    video_searches: List[str]


class ProbabilityItem(BaseModel):
    percent: int
    title: str
    description: str
    details: Optional[IssueDetails] = None


class WebResult(BaseModel):
    title: str
    url: str
    snippet: str


class DiagnosisPayload(BaseModel):
    full_analysis: str
    probabilities: List[ProbabilityItem]
    web_results: List[WebResult]
    timestamp: datetime
    model_number: str
    problem: str
    tech_name: Optional[str] = None
    job_number: Optional[str] = None


class IssueDetailResponse(BaseModel):
    details: IssueDetails


class DiagnosisResponse(DiagnosisPayload):
    message: str = "Diagnosis complete"


class IssueDetailsRequest(BaseModel):
    issue: str
    full_analysis: str


__all__ = [
    "DiagnosisRequest",
    "DiagnosisResponse",
    "WebResult",
    "ProbabilityItem",
    "DiagnosisPayload",
    "IssueDetails",
    "IssueDetailResponse",
    "IssueDetailsRequest",
]


