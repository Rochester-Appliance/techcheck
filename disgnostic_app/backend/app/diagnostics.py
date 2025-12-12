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
            r"\*\*Failure Signals?\s*/\s*Why it matches:\*\*(.*?)(?=\*\*|$)",
            r"Detailed Explanation:\s*(.*?)(?=\n\s*[A-Z][^:]{0,40}:|$)",
            r"Failure Signals?\s*/\s*Why it matches:\s*(.*?)(?=\n\s*[A-Z][^:]{0,40}:|$)",
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
            r"\*\*Parts\s*\+\s*Compatibility Notes:\*\*(.*?)(?=\*\*|$)",
            r"Parts Needed:\s*(.*?)(?=\n\s*(?:Verification|Step|Safety|Video)[^\n]*:|$)",
            r"Parts\s*\+\s*Compatibility Notes:\s*(.*?)(?=\n\s*(?:Verification|Step|Safety|Video)[^\n]*:|$)",
        ],
        section,
    ) or ""
    verify_block = _extract(
        [
            r"\*\*Verification Steps:\*\*(.*?)(?=\*\*|$)",
            r"\*\*Verification Checklist:\*\*(.*?)(?=\*\*|$)",
            r"Verification Steps:\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts)[^\n]*:|$)",
            r"Verification Checklist:\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts)[^\n]*:|$)",
        ],
        section,
    ) or ""
    repair_block = _extract(
        [
            r"\*\*Step-by-Step Repair:\*\*(.*?)(?=\*\*|$)",
            r"\*\*Step-by-Step Repair\s*/\s*Remedy:\*\*(.*?)(?=\*\*|$)",
            r"Step[- ]by[- ]Step Repair:\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|$)",
            r"Step[- ]by[- ]Step Repair\s*/\s*Remedy:\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|$)",
        ],
        section,
    ) or ""
    safety_block = _extract(
        [
            r"\*\*Safety Warnings?:\*\*(.*?)(?=\*\*|$)",
            r"\*\*Safety\s*/\s*Gotchas:\*\*(.*?)(?=\*\*|$)",
            r"Safety Warnings?:\s*(.*?)(?=\n\s*(?:Video|Step|Parts|Verification)[^\n]*:|$)",
            r"Safety\s*/\s*Gotchas:\s*(.*?)(?=\n\s*(?:Video|Step|Parts|Verification)[^\n]*:|$)",
        ],
        section,
    ) or ""
    video_block = _extract(
        [
            r"\*\*Video Resources?:\*\*(.*?)(?=\*\*|$)",
            r"\*\*Video\s*/\s*Further Study:\*\*(.*?)(?=\*\*|$)",
            r"Video Resources?:\s*(.*)$",
            r"Video\s*/\s*Further Study:\s*(.*)$",
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

    job_context_lines: List[str] = []
    if tech_name:
        job_context_lines.append(f"Technician on site: {tech_name}")
    if job_number:
        job_context_lines.append(f"Job/WO #: {job_number}")
    job_context = "\n".join(job_context_lines) if job_context_lines else "Technician/job identifiers not provided."

    diagnostic_prompt = f"""You are an expert appliance repair technician with 20+ years of field calls on refrigerators, laundry units, cooking appliances and HVAC-adjacent systems.

Model Number: {model_number}
Reported Symptoms (verbatim from technician/customer): {problem_description}
Job Context: {job_context}

Your task:
- Use the latest field intelligence, service bulletins, and parts data for THIS exact model/suffix.
- Run web_search when you need additional confirmation on known failure rates, updated part supersessions, or service bulletins.
- Produce diagnostic output that a field tech can follow quickly and easily.

LANGUAGE GUIDELINES (CRITICAL - follow strictly):
- Write in plain, simple English that any field technician can understand in under 10 seconds per bullet.
- Use everyday terms: "safety cutoff" instead of "TCO", "heating coil" instead of "resistive heating element".
- When mentioning technical readings, explain simply: "Check with multimeter - should show around 10-12 ohms" not "Ohm the element: expected 10-12Ω".
- Keep each bullet point to 1-2 short sentences maximum.
- Use "Check if..." or "Look for..." instead of "Verify that the component exhibits...".
- Avoid jargon and abbreviations - spell things out in plain language.
- If you must use a technical term, briefly explain what it means.

RESPONSE FORMAT (strict):

1. **PROBABILITY DISTRIBUTION** (3-6 lines; must sum to 100%)
   - Format: [XX%] Issue Title | One-line symptom link + failure mode
   - Weight the percentages using prevalence data (common service calls, recalls, known bulletins). Call out when an issue is rare but high-impact.

2. **DETAILED BREAKDOWN FOR EACH ISSUE (in descending probability)**  
   Use the structure below for *every* issue:

   **Issue:** [Issue title]

   **Failure Signals / Why it matches:**  
   - Bullet list that ties the reported symptoms to physics of failure. Mention any audible/visual cues, ice patterns, thermal behavior, error codes, etc.
   - Include model-specific notes (e.g., “WRS325SDHZ08 uses harness W11650662 – brown heater lead backs out.”)

   **Difficulty:** [0-100] **Estimated Time:** [minutes or range]

   **Parts + Compatibility Notes:**  
   - Part #[exact number] – Description — include availability hints if known (e.g., “superseded to W11650662”, “requires matching color code”).  
   - Mention when part numbers change by model suffix; instruct tech to confirm tag if ambiguous.  
   - If no part is normally required, explicitly say “No replacement parts typically required.”

   **Verification Checklist:**  
   1. [Specific measurement, visual inspection, or diagnostic mode step with expected reading/value]  
   2. [...] (include at least three verification items; note required tools such as multimeter, clamp probe, manometer, etc.)

   **Step-by-Step Repair / Remedy:**  
   1. [Action with torque/spec or caution if applicable]  
   2. [...]  
   3. [...]

   **Safety / Gotchas:**  
   - [List energized circuits, sharp edges, refrigerant tubing, steam, etc. Include PPE reminders.]

   **Video / Further Study:**  
   - Direct YouTube links if discovered via web search, else “Search: <recommended query>”.

3. **SERVICE BULLETIN OR ESCALATION NOTES (final section)**  
   - Mention any recalls, service flashes, firmware updates, or when to escalate to sealed-system specialist.  
   - Highlight questions to ask the customer if data is missing (e.g., “Confirm if defrost drain ever ice-blocks”).

Expectations:
- Cite bulletins when you reference them.
- Never make up part numbers—if unsure, tell the tech to check the parts diagram.
- Use simple, actionable language (e.g., "Check the heating coil with a multimeter - it should read 10-12 ohms").
- Keep instructions short and easy to scan quickly.
- If information is missing, say what you're assuming."""

    system_prompt = (
        "You are a senior technician who explains things in simple, plain English. "
        "Write like you're talking to a fellow tech in the field - keep it short, clear, and practical. "
        "Avoid jargon and technical abbreviations. Use everyday words that anyone can understand. "
        "Follow the requested sections strictly. Use web_search for service bulletins and part info when needed."
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


