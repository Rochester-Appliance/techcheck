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


class VNVPart(BaseModel):
    item_number: str = Field(default="")
    part_number: str = Field(default="")
    description: Optional[str] = None
    qty_available: Optional[int] = None
    price: Optional[float] = None
    list_price: Optional[float] = None
    url: Optional[str] = None
    image_urls: List[str] = Field(default_factory=list)


class VNVDiagram(BaseModel):
    diagram_id: int
    section_name: str
    small_image_url: Optional[str] = None
    large_image_url: Optional[str] = None
    parts: List[VNVPart] = Field(default_factory=list)


class VNVModel(BaseModel):
    model_number: str
    model_description: Optional[str] = None
    manufacturer: Optional[str] = None
    model_id: int


class DiagramBundle(BaseModel):
    model: VNVModel
    diagrams: List[VNVDiagram]


class DiagramBundleRequest(BaseModel):
    model_number: str = Field(..., min_length=1)
    max_diagrams: int = Field(default=4, ge=1, le=12)
    max_parts_per_diagram: int = Field(default=12, ge=1, le=50)


class DiagramBundleResponse(DiagramBundle):
    pass


__all__ = [
    "DiagnosisRequest",
    "DiagnosisResponse",
    "WebResult",
    "ProbabilityItem",
    "DiagnosisPayload",
    "IssueDetails",
    "IssueDetailResponse",
    "IssueDetailsRequest",
    "DiagramBundleRequest",
    "DiagramBundleResponse",
    "VNVPart",
    "VNVDiagram",
    "VNVModel",
]


