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
    # Limit to top 3 suggestions for focused, high-quality results
    return structured[:3]


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
        """Extract list items from text - handles bullets, numbers, and newline-separated items."""
        if not text or not text.strip():
            return []

        items: List[str] = []

        # Try bullet points first (-, •, *)
        bullet_items = re.findall(r"[-•*]\s*(.+?)(?=\n\s*[-•*]|\n\n|\n\*\*|$)", text, re.DOTALL)
        if bullet_items:
            items = bullet_items

        # Try numbered lists with period (1., 2., etc.)
        if not items:
            numbered_items = re.findall(r"\d+\.\s*(.+?)(?=\n\s*\d+\.|\n\n|\n\*\*|$)", text, re.DOTALL)
            if numbered_items:
                items = numbered_items

        # Try numbered lists with parenthesis (1), 2), etc.)
        if not items:
            paren_items = re.findall(r"\d+\)\s*(.+?)(?=\n?\s*\d+\)|\n\n|\n\*\*|$)", text, re.DOTALL)
            if paren_items:
                items = paren_items

        # Try inline numbered format "1) ... 2) ... 3) ..." (no newlines)
        if not items:
            inline_items = re.split(r'\d+\)\s*', text)
            inline_items = [item.strip() for item in inline_items if item.strip() and len(item.strip()) > 10]
            if len(inline_items) > 1:
                items = inline_items

        # If still no items, try splitting by newlines (for plain text lists)
        if not items:
            lines = text.strip().split('\n')
            items = [line.strip() for line in lines if line.strip() and len(line.strip()) > 5]

        # Clean up each item
        cleaned = []
        for item in items:
            # Remove leading bullet/number if present (both . and ) formats)
            clean_item = re.sub(r'^[\d]+[.)]\s*|^[-•*]\s*', '', item.strip())
            # Remove trailing markdown artifacts
            clean_item = re.sub(r'\*\*$', '', clean_item).strip()
            # Skip headers and artifacts
            lower_item = clean_item.lower()
            if lower_item.startswith("/ remedy") or lower_item.startswith("remedy:"):
                continue
            if lower_item.startswith("/ repair") or lower_item.startswith("repair:"):
                continue
            if lower_item.startswith("step-by-step"):
                continue
            if clean_item and len(clean_item) > 10:
                cleaned.append(clean_item)

        return cleaned

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
            # Markdown bold headers
            r"\*\*Verification Steps?:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Verification Checklist:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*How to Verify:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Testing:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            # Plain text headers
            r"Verification Steps?:\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts|Repair)[^\n]*:|\Z)",
            r"Verification Checklist:\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts|Repair)[^\n]*:|\Z)",
            r"How to Verify:?\s*(.*?)(?=\n\s*(?:Step-by-Step|Safety|Video|Parts|Repair)[^\n]*:|\Z)",
        ],
        section,
    ) or ""
    repair_block = _extract(
        [
            # Markdown bold headers
            r"\*\*Step-by-Step Repair:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Step-by-Step Repair\s*/\s*Remedy:\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Repair Steps?:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Remedy:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*How to Fix:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            r"\*\*Repair Instructions?:?\*\*\s*(.*?)(?=\n\*\*[A-Z]|\Z)",
            # Plain text headers
            r"Step[- ]by[- ]Step Repair:?\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|\Z)",
            r"Repair Steps?:\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|\Z)",
            r"How to Fix:?\s*(.*?)(?=\n\s*(?:Safety|Video|Verification|Parts)[^\n]*:|\Z)",
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
- NEVER include URLs, website links, or tracking parameters in any text content (verification steps, repair steps, etc.)
- All instructions must be self-contained plain text - no external references needed.

RESPONSE FORMAT (strict):

1. **PROBABILITY DISTRIBUTION** (exactly 3 issues; must sum to 100%)
   - Format: [XX%] Issue Title | One-line symptom link + failure mode
   - Provide ONLY the top 3 most likely causes - no more, no less.
   - Weight the percentages using prevalence data (common service calls, recalls, known bulletins).
   - Focus on quality over quantity - each suggestion should be actionable and well-supported.

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
   Provide 4-6 specific, actionable verification steps. Each step MUST include:
   - What to check (component, connection, reading)
   - How to check it (tool, method, visual inspection)
   - Expected result (specific values, ranges, or visual signs)
   - What it means if the test fails
   
   Example format:
   1. "Check the defrost heater with a multimeter set to ohms - should read 20-30 ohms. If infinite (OL), the heater is open and needs replacement."
   2. "Look at the evaporator coils behind the freezer panel - if frost is only on one section, the defrost system is failing."
   3. "Listen for a click when unplugging the fridge - if no click from the compressor relay, it may be stuck."
   
   NEVER include URLs or website links in verification steps - only plain text instructions.

   **Step-by-Step Repair / Remedy:**  
   Provide 5-8 clear, numbered repair steps. Each step should:
   - Start with an action verb (Remove, Disconnect, Install, etc.)
   - Include specific details (screw sizes, connector colors, torque specs if relevant)
   - Warn about common mistakes
   
   Example:
   1. "Unplug the refrigerator and wait 5 minutes for capacitors to discharge."
   2. "Remove the 4 Phillips screws holding the back panel - keep them separate, they're different lengths."
   3. "Disconnect the white 2-pin connector from the old defrost heater."

   **Safety / Gotchas:**  
   List 2-4 specific safety warnings relevant to this repair:
   - Electrical hazards (voltage present, capacitor discharge)
   - Physical hazards (sharp edges, hot surfaces, heavy parts)
   - Refrigerant warnings if applicable
   - Required PPE (gloves, safety glasses)
   
   Be specific: "Sharp evaporator fins can cut - wear cut-resistant gloves" not just "Be careful."

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


def generate_verification_steps(
    model_number: str,
    issue_title: str,
    symptoms: str,
    *,
    client: Optional["OpenAI"] = None,
) -> Dict[str, List[str]]:
    """
    Generate focused verification steps for a specific issue.
    This is a sub-query that uses a targeted prompt for better quality.
    """
    if client is None:
        client = get_openai_client()

    prompt = f"""You are an expert appliance repair technician. Generate ONLY verification steps for diagnosing this specific issue.

Model Number: {model_number}
Issue to Verify: {issue_title}
Reported Symptoms: {symptoms}

Provide 4-6 specific, actionable verification steps. Each step MUST include:
- What to check (component, connection, reading)
- How to check it (tool, method, visual inspection)
- Expected result (specific values, ranges, or visual signs)
- What it means if the test fails

Format each step as a clear, numbered instruction. Use plain English.

Example format:
1. Check the defrost heater with a multimeter set to ohms - should read 20-30 ohms. If infinite (OL), the heater is open and needs replacement.
2. Look at the evaporator coils behind the freezer panel - if frost is only on one section, the defrost system is failing.

Also provide 1-3 relevant safety warnings if applicable (e.g., unplug before testing, sharp edges, etc.)

RESPONSE FORMAT (strict JSON):
{{
  "verify_steps": ["step 1...", "step 2...", ...],
  "safety_warnings": ["warning 1...", "warning 2..."]
}}"""

    system_prompt = "You are a senior appliance technician. Return ONLY valid JSON with verify_steps and safety_warnings arrays. No markdown, no explanation."

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            ],
            max_output_tokens=2000,
        )
    except Exception as exc:
        logger.exception("Verification sub-query failed")
        raise DiagnosticError(f"Verification sub-query failed: {exc}")

    output_text = getattr(response, "output_text", None) or ""
    if not output_text:
        try:
            outputs = getattr(response, "output", []) or []
            for item in outputs:
                for content in getattr(item, "content", []) or []:
                    if hasattr(content, "text"):
                        output_text = getattr(content, "text", "")
                        break
        except Exception:
            pass

    # Parse JSON response
    try:
        # Clean up potential markdown code blocks
        cleaned = output_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        return {
            "verify_steps": result.get("verify_steps", []),
            "safety_warnings": result.get("safety_warnings", []),
        }
    except json.JSONDecodeError:
        logger.warning("Failed to parse verification response as JSON: %s", output_text[:500])
        # Fallback: try to extract steps from plain text
        lines = output_text.strip().split('\n')
        steps = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
        return {"verify_steps": steps[:6], "safety_warnings": []}


def generate_repair_steps(
    model_number: str,
    issue_title: str,
    symptoms: str,
    *,
    client: Optional["OpenAI"] = None,
) -> Dict[str, List[str]]:
    """
    Generate focused repair steps for a specific issue.
    This is a sub-query that uses a targeted prompt for better quality.
    """
    if client is None:
        client = get_openai_client()

    prompt = f"""You are an expert appliance repair technician. Generate ONLY step-by-step repair instructions for fixing this specific issue.

Model Number: {model_number}
Issue to Repair: {issue_title}
Reported Symptoms: {symptoms}

Provide 5-8 clear, numbered repair steps. Each step should:
- Start with an action verb (Remove, Disconnect, Install, Test, etc.)
- Include specific details (screw types, connector colors, torque specs if relevant)
- Warn about common mistakes
- Be in logical order from start to finish

Use plain English that any technician can follow quickly.

Example format:
1. Unplug the refrigerator and wait 5 minutes for capacitors to discharge.
2. Remove the 4 Phillips screws holding the back panel - keep them separate, they're different lengths.
3. Disconnect the white 2-pin connector from the old defrost heater - note which wire goes where.

Also provide 2-4 relevant safety warnings (electrical hazards, sharp edges, heavy parts, etc.)

RESPONSE FORMAT (strict JSON):
{{
  "repair_steps": ["step 1...", "step 2...", ...],
  "safety_warnings": ["warning 1...", "warning 2..."]
}}"""

    system_prompt = "You are a senior appliance technician. Return ONLY valid JSON with repair_steps and safety_warnings arrays. No markdown, no explanation."

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": [{"type": "input_text", "text": system_prompt}]},
                {"role": "user", "content": [{"type": "input_text", "text": prompt}]},
            ],
            max_output_tokens=2000,
        )
    except Exception as exc:
        logger.exception("Repair sub-query failed")
        raise DiagnosticError(f"Repair sub-query failed: {exc}")

    output_text = getattr(response, "output_text", None) or ""
    if not output_text:
        try:
            outputs = getattr(response, "output", []) or []
            for item in outputs:
                for content in getattr(item, "content", []) or []:
                    if hasattr(content, "text"):
                        output_text = getattr(content, "text", "")
                        break
        except Exception:
            pass

    # Parse JSON response
    try:
        # Clean up potential markdown code blocks
        cleaned = output_text.strip()
        if cleaned.startswith("```"):
            cleaned = cleaned.split("```")[1]
            if cleaned.startswith("json"):
                cleaned = cleaned[4:]
        cleaned = cleaned.strip()
        
        result = json.loads(cleaned)
        return {
            "repair_steps": result.get("repair_steps", []),
            "safety_warnings": result.get("safety_warnings", []),
        }
    except json.JSONDecodeError:
        logger.warning("Failed to parse repair response as JSON: %s", output_text[:500])
        # Fallback: try to extract steps from plain text
        lines = output_text.strip().split('\n')
        steps = [line.strip() for line in lines if line.strip() and len(line.strip()) > 10]
        return {"repair_steps": steps[:8], "safety_warnings": []}


__all__ = [
    "DiagnosticError",
    "search_web",
    "perform_diagnostic_analysis",
    "extract_issue_details",
    "get_openai_client",
    "generate_verification_steps",
    "generate_repair_steps",
]


