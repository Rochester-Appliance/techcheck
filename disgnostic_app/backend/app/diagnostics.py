from __future__ import annotations

import json
import logging
import re
import urllib.parse
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence, Tuple

import requests
from bs4 import BeautifulSoup

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - handled at runtime
    OpenAI = None  # type: ignore

from .config import get_settings
from .schemas import IssueDetails, ProbabilityItem, WebResult


logger = logging.getLogger(__name__)


class DiagnosticError(RuntimeError):
    """Raised when the diagnostic workflow fails."""


def get_openai_client() -> "OpenAI":
    settings = get_settings()
    api_key = settings.openai_api_key
    if not api_key:
        raise DiagnosticError("OPENAI_API_KEY is not configured. Set env variable or api.txt.")
    if OpenAI is None:
        raise DiagnosticError("openai package is not installed.")
    return OpenAI(api_key=api_key)


def search_web(query: str, num_results: int = 10, timeout: int = 10) -> List[WebResult]:
    enhanced_query = f"{query} appliance parts troubleshooting repair"
    search_url = f"https://html.duckduckgo.com/html/?q={urllib.parse.quote_plus(enhanced_query)}"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}

    try:
        response = requests.get(search_url, headers=headers, timeout=timeout)
        response.raise_for_status()
    except Exception as exc:  # pragma: no cover - network
        logger.warning("DuckDuckGo search failed: %s", exc)
        return []

    soup = BeautifulSoup(response.content, "html.parser")
    results: List[WebResult] = []

    for result in soup.find_all("div", class_="result")[:num_results]:
        title_elem = result.find("a", class_="result__a")
        snippet_elem = result.find("a", class_="result__snippet")

        if title_elem and snippet_elem:
            results.append(
                WebResult(
                    title=title_elem.get_text().strip(),
                    url=title_elem.get("href", ""),
                    snippet=snippet_elem.get_text().strip(),
                )
            )

    return results


def _parse_probability_distribution(analysis_text: str) -> List[Tuple[int, str, str]]:
    probability_pattern = r"\[(\d+)%\]\s*([^|]+)\|\s*([^\n]+)"
    probabilities = re.findall(probability_pattern, analysis_text, re.MULTILINE)

    if not probabilities:
        probability_pattern = r"\[(\d+)%\]\s*([^\-\n]+?)(?:\s*-\s*|\s*:\s*)([^\n]+)"
        probabilities = re.findall(probability_pattern, analysis_text, re.MULTILINE)

    structured: List[Tuple[int, str, str]] = []
    for match in probabilities:
        try:
            percent = int(match[0])
            title = match[1].strip()
            desc = match[2].strip()
        except (ValueError, IndexError):
            continue
        structured.append((percent, title, desc))

    structured.sort(key=lambda item: item[0], reverse=True)
    return structured


def extract_issue_details(full_analysis: str, issue_title: str) -> IssueDetails:
    issue_patterns = [
        rf"###?\s*Issue:\s*{re.escape(issue_title)}(.*?)(?=###?\s*Issue:|$)",
        rf"\*\*Issue:\s*{re.escape(issue_title)}\*\*(.*?)(?=\*\*Issue:|$)",
        rf"Issue:\s*{re.escape(issue_title)}(.*?)(?=Issue:|$)",
    ]

    section: Optional[str] = None
    for pattern in issue_patterns:
        match = re.search(pattern, full_analysis, re.DOTALL | re.IGNORECASE)
        if match:
            section = match.group(1)
            break

    if not section:
        section = full_analysis

    def _extract(patterns: Sequence[str], text: str) -> Optional[str]:
        for pattern in patterns:
            match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
            if match:
                return match.group(1).strip()
        return None

    difficulty = _extract(
        [r"\*\*Difficulty:\*\*\s*([\d/]+)", r"Difficulty:\s*([\d/]+)", r"Difficulty\s*[-–:]\s*([\d/]+)"],
        section,
    )
    time_needed = _extract(
        [
            r"\*\*Estimated Time:\*\*\s*([^\n]+)",
            r"Estimated Time:\s*([^\n]+)",
            r"Time\s*Required\s*[:\-]\s*([^\n]+)",
        ],
        section,
    )
    explanation = _extract(
        [
            r"\*\*Detailed Explanation:\*\*(.*?)(?=\*\*|$)",
            r"Detailed Explanation:\s*(.*?)(?=\n\s*[A-Z][^:]{0,40}:|$)",
        ],
        section,
    )

    def _extract_list(text: str) -> Sequence[str]:
        items = re.findall(r"[-•*]\s*(.+?)(?=\n[-•*]|\n\n|\*\*|$)", text, re.DOTALL)
        if not items:
            items = re.findall(r"\d+\.\s*(.+?)(?=\n\d+\.|\n\n|\*\*|$)", text, re.DOTALL)
        return [item.strip() for item in items if item.strip()]

    parts_block = _extract(
        [
            r"\*\*Parts Needed:\*\*(.*?)(?=\*\*|$)",
            r"Parts Needed:\s*(.*?)(?=\n\s*(?:Verification|Step|Safety|Video)[^\n]*:|$)",
        ],
        section,
    ) or ""
    verify_block = _extract(
        [
            r"\*\*Verification Steps:\*\*(.*?)(?=\*\*|$)",
            r"Verification Steps:\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts)[^\n]*:|$)",
        ],
        section,
    ) or ""
    repair_block = _extract(
        [
            r"\*\*Step-by-Step Repair:\*\*(.*?)(?=\*\*|$)",
            r"Step[- ]by[- ]Step Repair:\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|$)",
        ],
        section,
    ) or ""
    safety_block = _extract(
        [
            r"\*\*Safety Warnings?:\*\*(.*?)(?=\*\*|$)",
            r"Safety Warnings?:\s*(.*?)(?=\n\s*(?:Video|Step|Parts|Verification)[^\n]*:|$)",
        ],
        section,
    ) or ""
    video_block = _extract(
        [
            r"\*\*Video Resources?:\*\*(.*?)(?=\*\*|$)",
            r"Video Resources?:\s*(.*)$",
        ],
        section,
    ) or ""

    video_items = re.findall(
        r"[-•*]\s*(?:Search:\s*)?[\"']?(.+?)[\"']?(?:\s+on YouTube)?(?=\n[-•*]|\n\n|\*\*|$)",
        video_block,
        re.DOTALL,
    )

    return IssueDetails(
        difficulty=difficulty,
        time=time_needed,
        explanation=explanation,
        parts=list(_extract_list(parts_block)),
        verify_steps=list(_extract_list(verify_block)),
        repair_steps=list(_extract_list(repair_block)),
        safety_warnings=list(_extract_list(safety_block)),
        video_searches=[item.strip() for item in video_items if item.strip()],
    )


def perform_diagnostic_analysis(
    model_number: str,
    problem_description: str,
    *,
    tech_name: Optional[str] = None,
    job_number: Optional[str] = None,
    client: Optional["OpenAI"] = None,
) -> Dict:
    if client is None:
        client = get_openai_client()

    diagnostic_prompt = f"""You are an expert appliance repair technician with 20+ years experience.

Model: {model_number}
Problem: {problem_description}

Search the web for the latest repair information, part numbers, and troubleshooting guides for this specific model.

Provide a HIGHLY DETAILED diagnostic analysis in this EXACT format:

1. **PROBABILITY DISTRIBUTION** (Must sum to 100%)
   Format: [XX%] Issue Title | One-line description
   List 3-5 issues in descending order

2. **For EACH issue above, provide COMPLETE details:**

   **Issue: [Issue Title]**
   
   **Difficulty:** [X/100]
   **Estimated Time:** [X minutes]
   
   **Detailed Explanation:**
   [2-3 sentences explaining the issue and why these symptoms indicate this problem]
   
   **Parts Needed:**
   - Part Name: [Exact part number if available, e.g., "5304475102"] - Description
   - [Additional parts if needed]
   
   **Verification Steps:**
   • Step 1: [Specific test to confirm issue]
   • Step 2: [Another verification method]
   • Step 3: [Final confirmation check]
   
   **Step-by-Step Repair:**
   1. [First step with specifics]
   2. [Second step with details]
   3. [Continue with clear instructions]
   
   **Safety Warnings:**
   - [Any electrical/mechanical safety concerns]
   
   **Video Resources:**
   - Search: "[Model] [issue] repair" on YouTube
   - Search: "[Part name] replacement tutorial"

Repeat this format for ALL issues. Be extremely specific with part numbers, verification steps, and repair instructions."""

    system_prompt = (
        "You are an expert appliance diagnostician. Provide extremely detailed, actionable guidance "
        "with specific part numbers and step-by-step instructions."
    )

    message_payload = [
        {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
        {"role": "user", "content": [{"type": "input_text", "text": diagnostic_prompt}]},
    ]

    try:
        response = client.responses.create(
            model="gpt-5",
            input=message_payload,
            reasoning={"effort": "medium"},
            tools=[{"type": "web_search"}],
            max_output_tokens=8000,
            max_tool_calls=6,
        )
    except Exception as exc:  # pragma: no cover - network
        logger.exception("OpenAI diagnostic request failed")
        raise DiagnosticError(f"OpenAI diagnostic request failed: {exc}")

    analysis = getattr(response, "output_text", None) or ""
    if not analysis:
        try:
            outputs = getattr(response, "output", []) or []
            collected: List[str] = []
            for item in outputs:
                content_items = getattr(item, "content", []) or []
                for content in content_items:
                    if isinstance(content, dict):
                        text_value = content.get("text") or content.get("value")
                        if text_value:
                            collected.append(str(text_value))
                        continue

                    text_obj = getattr(content, "text", None)
                    if text_obj and getattr(text_obj, "value", None):
                        collected.append(text_obj.value)
                    elif isinstance(text_obj, str):
                        collected.append(text_obj)
                    elif hasattr(content, "value") and getattr(content, "value"):
                        collected.append(str(content.value))
            analysis = "\n".join(collected).strip()
        except Exception:  # pragma: no cover - defensive fallback
            analysis = ""
    if not analysis:
        response_overview: Dict[str, Any] = {
            "status": getattr(response, "status", None),
            "output_types": [getattr(item, "type", type(item).__name__) for item in getattr(response, "output", []) or []],
        }
        usage = getattr(response, "usage", None)
        if usage is not None and hasattr(usage, "model_dump"):
            response_overview["usage"] = usage.model_dump()
        try:
            logger.error(
                "LLM response missing analysis text. Overview: %s",
                json.dumps(response_overview)[:2000],
            )
        except Exception:  # pragma: no cover - logging safeguard
            logger.error("LLM response missing analysis text. Raw response status: %s", response_overview)
        raise DiagnosticError("Received empty diagnostic analysis from LLM.")

    structured_probs = _parse_probability_distribution(analysis)

    web_results = search_web(f"{model_number} {problem_description} repair parts", 15)

    def _youtube_links(limit: int = 5) -> List[str]:
        links: List[str] = []
        seen: set[str] = set()
        for result in web_results:
            url_lower = result.url.lower()
            if "youtube.com/watch" not in url_lower and "youtu.be/" not in url_lower:
                continue
            label = result.title.strip() or result.url
            markdown_link = f"[{label}]({result.url})"
            if markdown_link.lower() in seen:
                continue
            seen.add(markdown_link.lower())
            links.append(markdown_link)
            if len(links) >= limit:
                break
        return links

    youtube_markdown_links = _youtube_links()
    if not youtube_markdown_links:
        supplemental_results = search_web(
            f"{model_number} {problem_description} repair video site:youtube.com", 8
        )
        if supplemental_results:
            web_results.extend(supplemental_results)
            youtube_markdown_links = _youtube_links()

    video_lookup_cache: Dict[str, List[str]] = {}

    def _normalise_video_query(value: str) -> Optional[str]:
        cleaned = value.replace("“", "").replace("”", "").strip()
        cleaned = re.sub(r"\bon youtube\b", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = cleaned.strip('"')
        if not cleaned:
            return None
        return cleaned

    def _fetch_direct_video_links(query: str, per_query_limit: int = 2) -> List[str]:
        if not query:
            return []
        if query in video_lookup_cache:
            return video_lookup_cache[query]
        try:
            response = requests.get(
                "https://yewtu.be/api/v1/search",
                params={"q": query, "type": "video", "region": "US"},
                timeout=8,
            )
            response.raise_for_status()
            data = response.json()
        except Exception:
            video_lookup_cache[query] = []
            return []

        links: List[str] = []
        for item in data:
            video_id = item.get("videoId")
            title = item.get("title")
            if not video_id or not title:
                continue
            url = f"https://www.youtube.com/watch?v={video_id}"
            markdown_link = f"[{title}]({url})"
            if markdown_link in links:
                continue
            links.append(markdown_link)
            if len(links) >= per_query_limit:
                break

        video_lookup_cache[query] = links
        return links

    def _resolve_direct_videos(queries: Sequence[str], fallback_query: str) -> List[str]:
        aggregated: List[str] = []
        seen: set[str] = set()

        for raw in queries:
            normalized = _normalise_video_query(raw)
            if not normalized:
                continue
            for link in _fetch_direct_video_links(normalized):
                key = link.lower()
                if key in seen:
                    continue
                seen.add(key)
                aggregated.append(link)

        if not aggregated and fallback_query:
            for link in _fetch_direct_video_links(fallback_query):
                key = link.lower()
                if key in seen:
                    continue
                seen.add(key)
                aggregated.append(link)

        return aggregated

    probabilities: List[ProbabilityItem] = []
    for percent, title, description in structured_probs:
        details = extract_issue_details(analysis, title)
        existing_video_entries = list(details.video_searches)

        direct_video_links = _resolve_direct_videos(
            existing_video_entries,
            fallback_query=f"{model_number} {title} repair",
        )

        if youtube_markdown_links or direct_video_links:
            enriched_videos: List[str] = []
            seen_video: set[str] = set()

            for entry in existing_video_entries:
                normalized = entry.strip()
                if not normalized:
                    continue
                key = normalized.lower()
                if key in seen_video:
                    continue
                seen_video.add(key)
                enriched_videos.append(normalized)

            for link in youtube_markdown_links:
                key = link.lower()
                if key in seen_video:
                    continue
                seen_video.add(key)
                enriched_videos.append(link)

            for link in direct_video_links:
                key = link.lower()
                if key in seen_video:
                    continue
                seen_video.add(key)
                enriched_videos.append(link)

            details.video_searches = enriched_videos

        probabilities.append(
            ProbabilityItem(
                percent=percent,
                title=title,
                description=description,
                details=details,
            )
        )

    payload = {
        "full_analysis": analysis,
        "probabilities": [prob.model_dump() for prob in probabilities],
        "web_results": [result.model_dump() for result in web_results],
        "timestamp": datetime.utcnow(),
        "model_number": model_number,
        "problem": problem_description,
        "tech_name": tech_name,
        "job_number": job_number,
    }

    logger.debug("Diagnostic payload generated: %s", json.dumps(payload, default=str)[:5000])

    return payload


__all__ = [
    "DiagnosticError",
    "search_web",
    "perform_diagnostic_analysis",
    "extract_issue_details",
    "get_openai_client",
]


