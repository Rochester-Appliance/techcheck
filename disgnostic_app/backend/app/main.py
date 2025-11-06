from __future__ import annotations

import logging
from typing import Any, Dict

from fastapi import FastAPI, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware

from .diagnostics import DiagnosticError, extract_issue_details, perform_diagnostic_analysis
from .schemas import (
    DiagnosisRequest,
    DiagnosisResponse,
    IssueDetailResponse,
    IssueDetailsRequest,
)


logger = logging.getLogger(__name__)

app = FastAPI(
    title="TechCheck Diagnostic API",
    description="FastAPI backend powering the TechCheck diagnostic experience",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["system"])
async def healthcheck() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/diagnose", response_model=DiagnosisResponse, tags=["diagnostics"])
async def diagnose(payload: DiagnosisRequest) -> DiagnosisResponse:
    try:
        result: Dict[str, Any] = await run_in_threadpool(
            perform_diagnostic_analysis,
            payload.model_number,
            payload.problem_description,
            tech_name=payload.tech_name,
            job_number=payload.job_number,
        )
    except DiagnosticError as exc:
        logger.warning("Diagnostic error: %s", exc)
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected diagnostic error")
        raise HTTPException(status_code=500, detail="Diagnostic processing failed") from exc

    return DiagnosisResponse(**result)


@app.post("/diagnose/issue-details", response_model=IssueDetailResponse, tags=["diagnostics"])
async def get_issue_details(payload: IssueDetailsRequest) -> IssueDetailResponse:
    details = await run_in_threadpool(
        extract_issue_details,
        payload.full_analysis,
        payload.issue,
    )
    return IssueDetailResponse(details=details)


__all__ = ["app"]


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


