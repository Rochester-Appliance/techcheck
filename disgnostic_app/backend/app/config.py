from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional


REPO_ROOT = Path(__file__).resolve().parents[3]
API_KEY_FILE = REPO_ROOT / "api.txt"


class Settings:
    """Application settings loaded from the environment with sensible fallbacks."""

    def __init__(self) -> None:
        self._openai_api_key_env = os.getenv("OPENAI_API_KEY")

    @property
    def openai_api_key(self) -> Optional[str]:
        if self._openai_api_key_env:
            return self._openai_api_key_env
        try:
            return API_KEY_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["get_settings"]


