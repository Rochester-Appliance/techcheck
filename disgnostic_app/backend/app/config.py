from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

# Load .env file from backend directory or parent directories
BACKEND_ROOT = Path(__file__).resolve().parents[1]
REPO_ROOT = Path(__file__).resolve().parents[3]
API_KEY_FILE = REPO_ROOT / "api.txt"

# Try to load .env from multiple locations
for env_path in [
    BACKEND_ROOT / ".env",           # backend/.env
    REPO_ROOT / ".env",               # repo root/.env  
    REPO_ROOT / "techcheck.env",      # repo root/techcheck.env
]:
    if env_path.exists():
        load_dotenv(env_path)
        break


class Settings:
    """Application settings loaded from the environment with sensible fallbacks."""

    def __init__(self) -> None:
        self._openai_api_key_env = os.getenv("OPENAI_API_KEY")
        self._vnv_api_base_url_env = os.getenv("VNV_API_BASE_URL")
        # Stripe keys - loaded from environment variables (set in .env locally or hosting platform)
        self._stripe_secret_key = os.getenv("STRIPE_SECRET_KEY", "")
        self._stripe_publishable_key = os.getenv("STRIPE_PUBLISHABLE_KEY", "")
        self._stripe_webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        # YouTube Data API key
        self._youtube_api_key = os.getenv("YOUTUBE_API_KEY", "")

    @property
    def openai_api_key(self) -> Optional[str]:
        if self._openai_api_key_env:
            return self._openai_api_key_env
        try:
            return API_KEY_FILE.read_text(encoding="utf-8").strip()
        except FileNotFoundError:
            return None

    @property
    def vnv_api_base_url(self) -> str:
        base_url = self._vnv_api_base_url_env or "https://rocparts-api.onrender.com/api"
        return base_url.rstrip("/")

    @property
    def stripe_secret_key(self) -> str:
        return self._stripe_secret_key

    @property
    def stripe_publishable_key(self) -> str:
        return self._stripe_publishable_key

    @property
    def stripe_webhook_secret(self) -> str:
        return self._stripe_webhook_secret

    @property
    def youtube_api_key(self) -> str:
        return self._youtube_api_key


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


__all__ = ["get_settings"]
