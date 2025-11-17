from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any, Dict, List, Optional

import requests

from .config import get_settings


logger = logging.getLogger(__name__)


class VNVClientError(RuntimeError):
    """Raised when the V&V proxy API request fails."""


def _as_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    text = str(value).strip()
    if not text:
        return None
    try:
        return int(float(text))
    except (TypeError, ValueError):
        return None


def _as_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip()
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        return None


def _normalize_path(path: str) -> str:
    return path if path.startswith("/") else f"/{path}"


class VNVClient:
    def __init__(self, base_url: str, timeout: float = 25.0) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

    def _request(self, path: str, payload: Dict[str, Any]) -> Any:
        url = f"{self.base_url}{_normalize_path(path)}"
        try:
            response = self._session.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            logger.warning("V&V request failed: %s", exc)
            raise VNVClientError("Failed to reach V&V proxy service") from exc

        if response.status_code >= 400:
            logger.warning("V&V request error %s: %s", response.status_code, response.text)
            message = self._extract_error_message(response)
            raise VNVClientError(f"V&V API error ({response.status_code}): {message}")

        try:
            data = response.json()
        except ValueError as exc:
            logger.warning("Invalid JSON payload from V&V: %s", exc)
            raise VNVClientError("V&V API returned invalid JSON") from exc

        if isinstance(data, dict) and data.get("error"):
            raise VNVClientError(str(data["error"]))

        return data

    @staticmethod
    def _extract_error_message(response: requests.Response) -> str:
        try:
            payload = response.json()
        except ValueError:
            return response.text or "Unexpected error"

        if isinstance(payload, dict):
            return str(payload.get("error") or payload.get("message") or response.text or "Unexpected error")
        return response.text or "Unexpected error"

    def search_models(self, model_number: str) -> List[Dict[str, Any]]:
        data = self._request("/model-search", {"modelNumber": model_number})
        return data if isinstance(data, list) else []

    def get_diagrams(self, model_number: str, model_id: int) -> List[Dict[str, Any]]:
        payload = {"modelNumber": model_number, "modelId": model_id}
        data = self._request("/get-diagrams", payload)
        return data if isinstance(data, list) else []

    def get_diagram_parts(self, model_number: str, model_id: int, diagram_id: int) -> Dict[str, Any]:
        payload = {
            "modelNumber": model_number,
            "modelId": model_id,
            "diagramId": diagram_id,
        }
        data = self._request("/get-diagram-parts", payload)
        return data if isinstance(data, dict) else {}

    def fetch_diagram_bundle(
        self,
        model_number: str,
        max_diagrams: int,
        max_parts_per_diagram: int,
    ) -> Dict[str, Any]:
        matches = self.search_models(model_number)
        if not matches:
            raise VNVClientError(f"No diagram data found for model '{model_number}'.")

        selected = self._choose_match(model_number, matches)
        diagrams = self.get_diagrams(selected["modelNumber"], selected["modelId"])[:max_diagrams]
        if not diagrams:
            raise VNVClientError(
                f"No diagrams available for model '{selected['modelNumber']}'."
            )

        result_diagrams: List[Dict[str, Any]] = []
        for diagram in diagrams:
            diagram_id = diagram.get("diagramId")
            if diagram_id is None:
                continue

            raw_parts = self.get_diagram_parts(
                selected["modelNumber"], selected["modelId"], diagram_id
            )

            transformed_parts = self._transform_parts(raw_parts, max_parts_per_diagram)

            result_diagrams.append(
                {
                    "diagram_id": diagram_id,
                    "section_name": diagram.get("sectionName", "Diagram"),
                    "small_image_url": diagram.get("diagramSmallImage"),
                    "large_image_url": diagram.get("diagramLargeImage"),
                    "parts": transformed_parts,
                }
            )

        return {
            "model": {
                "model_number": selected.get("modelNumber"),
                "model_description": selected.get("modelDescription"),
                "manufacturer": selected.get("mfg"),
                "model_id": selected.get("modelId"),
            },
            "diagrams": result_diagrams,
        }

    def _transform_parts(
        self, raw_parts: Dict[str, Any], max_parts: int
    ) -> List[Dict[str, Any]]:
        items: List[Dict[str, Any]] = []
        for entry in raw_parts.values():
            if not isinstance(entry, dict):
                continue

            item_number = str(entry.get("itemNumber") or "").strip()
            part_number = str(entry.get("partNumber") or "").strip()

            image_field = entry.get("images")
            if isinstance(image_field, list):
                image_urls = [str(url) for url in image_field if url]
            elif isinstance(image_field, str) and image_field.strip():
                image_urls = [image_field.strip()]
            else:
                image_urls = []

            item = {
                "item_number": item_number,
                "part_number": part_number,
                "description": (entry.get("partDescription") or "").strip() or None,
                "qty_available": _as_int(entry.get("qtyTotal")),
                "price": _as_float(entry.get("price")),
                "list_price": _as_float(entry.get("listPrice")),
                "url": entry.get("url"),
                "image_urls": image_urls,
            }

            items.append(item)

        items.sort(key=_diagram_part_sort_key)
        if max_parts > 0:
            items = items[:max_parts]
        return items

    @staticmethod
    def _choose_match(model_number: str, matches: List[Dict[str, Any]]) -> Dict[str, Any]:
        lowered = model_number.replace("-", "").lower()
        for match in matches:
            candidate = str(match.get("modelNumber") or "").replace("-", "").lower()
            if candidate == lowered:
                return match
        return matches[0]


def _diagram_part_sort_key(item: Dict[str, Any]) -> Any:
    item_number = str(item.get("item_number") or "")
    numeric = _as_int(item_number)
    return (0, numeric) if numeric is not None else (1, item_number)


@lru_cache(maxsize=1)
def get_vnv_client() -> VNVClient:
    settings = get_settings()
    return VNVClient(settings.vnv_api_base_url)


__all__ = ["VNVClient", "VNVClientError", "get_vnv_client"]





