"""YouTube Data API v3 integration for fetching video search results."""

from __future__ import annotations

import logging
import re
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional

import httpx

from .config import get_settings

logger = logging.getLogger(__name__)

# Simple in-memory cache for YouTube results
_cache: Dict[str, tuple[List[Dict[str, Any]], datetime]] = {}
CACHE_TTL_HOURS = 24

YOUTUBE_API_BASE = "https://www.googleapis.com/youtube/v3"


class YouTubeAPIError(Exception):
    """Raised when YouTube API request fails."""


def _format_view_count(count: int) -> str:
    """Format view count to human readable string (e.g., 2.3K views)."""
    if count >= 1_000_000:
        return f"{count / 1_000_000:.1f}M views"
    elif count >= 1_000:
        return f"{count / 1_000:.1f}K views"
    else:
        return f"{count} views"


def _format_duration(iso_duration: str) -> str:
    """Convert ISO 8601 duration (PT5M30S) to readable format (5:30)."""
    if not iso_duration:
        return ""
    
    # Parse ISO 8601 duration: PT#H#M#S
    pattern = r"PT(?:(\d+)H)?(?:(\d+)M)?(?:(\d+)S)?"
    match = re.match(pattern, iso_duration)
    if not match:
        return ""
    
    hours = int(match.group(1) or 0)
    minutes = int(match.group(2) or 0)
    seconds = int(match.group(3) or 0)
    
    if hours > 0:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    else:
        return f"{minutes}:{seconds:02d}"


def _format_published_date(published_at: str) -> str:
    """Convert ISO date to relative time (e.g., '2 years ago')."""
    try:
        published = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        now = datetime.now(published.tzinfo)
        delta = now - published
        
        days = delta.days
        if days >= 365:
            years = days // 365
            return f"{years} year{'s' if years > 1 else ''} ago"
        elif days >= 30:
            months = days // 30
            return f"{months} month{'s' if months > 1 else ''} ago"
        elif days >= 7:
            weeks = days // 7
            return f"{weeks} week{'s' if weeks > 1 else ''} ago"
        elif days >= 1:
            return f"{days} day{'s' if days > 1 else ''} ago"
        else:
            hours = delta.seconds // 3600
            if hours >= 1:
                return f"{hours} hour{'s' if hours > 1 else ''} ago"
            else:
                return "Just now"
    except Exception:
        return ""


def _get_cache_key(query: str, max_results: int) -> str:
    """Generate a cache key for the search query."""
    return f"{query.lower().strip()}:{max_results}"


def _get_cached_results(cache_key: str) -> Optional[List[Dict[str, Any]]]:
    """Get cached results if still valid."""
    if cache_key in _cache:
        results, cached_at = _cache[cache_key]
        if datetime.now() - cached_at < timedelta(hours=CACHE_TTL_HOURS):
            logger.debug("Cache hit for YouTube query: %s", cache_key)
            return results
        else:
            # Expired, remove from cache
            del _cache[cache_key]
    return None


def _set_cache(cache_key: str, results: List[Dict[str, Any]]) -> None:
    """Cache the search results."""
    _cache[cache_key] = (results, datetime.now())
    
    # Simple cache size limit - remove oldest entries if over 100
    if len(_cache) > 100:
        oldest_key = min(_cache.keys(), key=lambda k: _cache[k][1])
        del _cache[oldest_key]


async def search_youtube_videos(
    query: str,
    max_results: int = 3,
) -> List[Dict[str, Any]]:
    """
    Search YouTube for videos matching the query.
    
    Args:
        query: Search query string
        max_results: Maximum number of results to return (default 3)
    
    Returns:
        List of video objects with id, title, thumbnail, channel, views, duration
    """
    settings = get_settings()
    api_key = settings.youtube_api_key
    
    if not api_key:
        logger.warning("YOUTUBE_API_KEY not configured, returning empty results")
        return []
    
    # Check cache first
    cache_key = _get_cache_key(query, max_results)
    cached = _get_cached_results(cache_key)
    if cached is not None:
        return cached
    
    # Enhance query for better appliance repair results
    enhanced_query = f"{query} repair how to"
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Step 1: Search for videos
            search_params = {
                "part": "snippet",
                "q": enhanced_query,
                "type": "video",
                "maxResults": max_results,
                "order": "relevance",
                "videoDuration": "medium",  # 4-20 minutes, good for tutorials
                "key": api_key,
            }
            
            search_resp = await client.get(
                f"{YOUTUBE_API_BASE}/search",
                params=search_params,
            )
            search_resp.raise_for_status()
            search_data = search_resp.json()
            
            if "items" not in search_data or not search_data["items"]:
                logger.info("No YouTube results for query: %s", query)
                return []
            
            # Extract video IDs for fetching additional details
            video_ids = [item["id"]["videoId"] for item in search_data["items"]]
            
            # Step 2: Get video details (duration, view count)
            details_params = {
                "part": "contentDetails,statistics",
                "id": ",".join(video_ids),
                "key": api_key,
            }
            
            details_resp = await client.get(
                f"{YOUTUBE_API_BASE}/videos",
                params=details_params,
            )
            details_resp.raise_for_status()
            details_data = details_resp.json()
            
            # Build details map
            details_map: Dict[str, Dict[str, Any]] = {}
            for item in details_data.get("items", []):
                video_id = item["id"]
                details_map[video_id] = {
                    "duration": item.get("contentDetails", {}).get("duration", ""),
                    "view_count": int(item.get("statistics", {}).get("viewCount", 0)),
                }
            
            # Build final results
            results: List[Dict[str, Any]] = []
            for item in search_data["items"]:
                video_id = item["id"]["videoId"]
                snippet = item["snippet"]
                details = details_map.get(video_id, {})
                
                results.append({
                    "video_id": video_id,
                    "title": snippet.get("title", ""),
                    "thumbnail_url": snippet.get("thumbnails", {}).get("medium", {}).get("url", ""),
                    "channel_name": snippet.get("channelTitle", ""),
                    "view_count": _format_view_count(details.get("view_count", 0)),
                    "duration": _format_duration(details.get("duration", "")),
                    "published_at": _format_published_date(snippet.get("publishedAt", "")),
                })
            
            # Cache the results
            _set_cache(cache_key, results)
            
            logger.info("Found %d YouTube videos for query: %s", len(results), query)
            return results
            
    except httpx.HTTPStatusError as exc:
        logger.error("YouTube API HTTP error: %s - %s", exc.response.status_code, exc.response.text)
        raise YouTubeAPIError(f"YouTube API error: {exc.response.status_code}") from exc
    except httpx.RequestError as exc:
        logger.error("YouTube API request failed: %s", exc)
        raise YouTubeAPIError(f"YouTube API request failed: {exc}") from exc
    except Exception as exc:
        logger.exception("Unexpected error in YouTube search")
        raise YouTubeAPIError(f"YouTube search failed: {exc}") from exc


__all__ = ["search_youtube_videos", "YouTubeAPIError"]

