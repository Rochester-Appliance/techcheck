from __future__ import annotations

import logging
from typing import Any, Dict, List
from urllib.parse import urlparse

import httpx
import stripe
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.concurrency import run_in_threadpool
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from pydantic import BaseModel

from .config import get_settings
from .diagnostics import DiagnosticError, extract_issue_details, perform_diagnostic_analysis
from .schemas import (
    DiagnosisRequest,
    DiagnosisResponse,
    IssueDetailResponse,
    IssueDetailsRequest,
    DiagramBundleRequest,
    DiagramBundleResponse,
)
from .vnv_client import VNVClientError, get_vnv_client
from .youtube import search_youtube_videos, YouTubeAPIError


logger = logging.getLogger(__name__)

# Initialize Stripe with secret key
settings = get_settings()
stripe.api_key = settings.stripe_secret_key


# ---------------------------------------------------------------------------
# Checkout Schemas
# ---------------------------------------------------------------------------

class CartItem(BaseModel):
    part_number: str
    description: str
    price: float  # in dollars
    quantity: int = 1
    image_url: str | None = None


class CheckoutRequest(BaseModel):
    items: List[CartItem]
    success_url: str
    cancel_url: str


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class StripeConfigResponse(BaseModel):
    publishable_key: str

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


@app.post("/parts/diagrams", response_model=DiagramBundleResponse, tags=["parts"])
async def fetch_parts_diagrams(payload: DiagramBundleRequest) -> DiagramBundleResponse:
    client = get_vnv_client()
    try:
        bundle = await run_in_threadpool(
            client.fetch_diagram_bundle,
            payload.model_number,
            payload.max_diagrams,
            payload.max_parts_per_diagram,
        )
    except VNVClientError as exc:
        logger.warning("V&V lookup failed: %s", exc)
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - defensive
        logger.exception("Unexpected V&V integration error")
        raise HTTPException(status_code=500, detail="Parts diagram lookup failed") from exc

    return DiagramBundleResponse.model_validate(bundle)


# ---------------------------------------------------------------------------
# Stripe Checkout Endpoints
# ---------------------------------------------------------------------------

@app.get("/checkout/config", response_model=StripeConfigResponse, tags=["checkout"])
async def get_stripe_config() -> StripeConfigResponse:
    """Return the Stripe publishable key for frontend initialization."""
    return StripeConfigResponse(publishable_key=settings.stripe_publishable_key)


@app.post("/checkout/create-session", response_model=CheckoutResponse, tags=["checkout"])
async def create_checkout_session(payload: CheckoutRequest) -> CheckoutResponse:
    """Create a Stripe Checkout Session for the cart items."""
    if not payload.items:
        raise HTTPException(status_code=400, detail="Cart is empty")

    # Build line items for Stripe
    line_items = []
    for item in payload.items:
        line_items.append({
            "price_data": {
                "currency": "usd",
                "unit_amount": int(item.price * 100),  # Stripe uses cents
                "product_data": {
                    "name": f"{item.part_number} - {item.description}",
                    "description": f"Part Number: {item.part_number}",
                    **({"images": [item.image_url]} if item.image_url else {}),
                },
            },
            "quantity": item.quantity,
        })

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            payment_method_types=["card"],
            line_items=line_items,
            success_url=payload.success_url + "?session_id={CHECKOUT_SESSION_ID}",
            cancel_url=payload.cancel_url,
            # Collect customer info
            billing_address_collection="required",
            shipping_address_collection={
                "allowed_countries": ["US", "CA"],
            },
            phone_number_collection={"enabled": True},
            # Generate invoice
            invoice_creation={"enabled": True},
        )
    except stripe.StripeError as exc:
        logger.error("Stripe checkout session creation failed: %s", exc)
        raise HTTPException(status_code=500, detail="Failed to create checkout session") from exc

    return CheckoutResponse(checkout_url=session.url, session_id=session.id)


@app.post("/checkout/webhook", tags=["checkout"])
async def stripe_webhook(request: Request) -> Dict[str, str]:
    """Handle Stripe webhook events."""
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    if not sig_header:
        raise HTTPException(status_code=400, detail="Missing Stripe signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.stripe_webhook_secret
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.SignatureVerificationError:
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        logger.info(
            "Checkout completed: session_id=%s, customer_email=%s, amount_total=%s",
            session.get("id"),
            session.get("customer_details", {}).get("email"),
            session.get("amount_total"),
        )
        # Here you could: save order to database, send confirmation email, etc.

    elif event["type"] == "invoice.paid":
        invoice = event["data"]["object"]
        logger.info(
            "Invoice paid: invoice_id=%s, invoice_pdf=%s",
            invoice.get("id"),
            invoice.get("invoice_pdf"),
        )

    return {"status": "success"}


# ---------------------------------------------------------------------------
# Image proxy – workaround for cross-origin blocking on V&V diagram images
# ---------------------------------------------------------------------------

ALLOWED_IMAGE_HOSTS = {"www.vvapplianceparts.com", "vvapplianceparts.com"}


@app.get("/proxy/image", tags=["parts"])
async def proxy_image(url: str = Query(..., description="Remote image URL to proxy")) -> Response:
    """Proxy external diagram images to bypass CORS restrictions."""
    parsed = urlparse(url)
    if parsed.hostname not in ALLOWED_IMAGE_HOSTS:
        raise HTTPException(status_code=400, detail="URL host not allowed")

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(url, follow_redirects=True)
            resp.raise_for_status()
    except httpx.HTTPError as exc:
        logger.warning("Failed to proxy image %s: %s", url, exc)
        raise HTTPException(status_code=502, detail="Failed to fetch remote image") from exc

    content_type = resp.headers.get("content-type", "image/jpeg")
    return Response(content=resp.content, media_type=content_type)


# ---------------------------------------------------------------------------
# YouTube Video Search Endpoint
# ---------------------------------------------------------------------------

class YouTubeVideo(BaseModel):
    video_id: str
    title: str
    thumbnail_url: str
    channel_name: str
    view_count: str
    duration: str
    published_at: str


class YouTubeSearchResponse(BaseModel):
    videos: List[YouTubeVideo]
    query: str


@app.get("/api/youtube/search", response_model=YouTubeSearchResponse, tags=["youtube"])
async def youtube_search(
    q: str = Query(..., description="Search query for YouTube videos"),
    max_results: int = Query(3, ge=1, le=10, description="Maximum number of results"),
) -> YouTubeSearchResponse:
    """Search YouTube for repair tutorial videos."""
    try:
        videos = await search_youtube_videos(q, max_results)
        return YouTubeSearchResponse(videos=videos, query=q)
    except YouTubeAPIError as exc:
        logger.warning("YouTube API error: %s", exc)
        # Return empty results instead of error - graceful degradation
        return YouTubeSearchResponse(videos=[], query=q)
    except Exception as exc:
        logger.exception("Unexpected YouTube search error")
        return YouTubeSearchResponse(videos=[], query=q)


__all__ = ["app"]


if __name__ == "__main__":  # pragma: no cover
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True)


