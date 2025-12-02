from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


def _ensure_openai_key_from_file() -> None:
    """If OPENAI_API_KEY is empty, try to load it from openai-key.txt at repo root."""
    if os.getenv("OPENAI_API_KEY"):
        return
    try:
        root = Path(__file__).resolve().parents[2]  # project root
        key_path = root / "openai-key.txt"
        if key_path.exists():
            content = key_path.read_text(encoding="utf-8").strip()
            if content:
                os.environ["OPENAI_API_KEY"] = content
    except Exception:
        # Silent fail; downstream will raise a clearer error
        pass


def _load_env_file(filename: str, keys: set[str]) -> None:
    """
    Load KEY=VALUE pairs from a text file at the project root into os.environ,
    but only for keys in the provided set and only when they are not already set.
    Lines starting with '#' or blank lines are ignored.
    """
    try:
        root = Path(__file__).resolve().parents[2]
        path = root / filename
        if not path.exists():
            return
        for line in path.read_text(encoding="utf-8").splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith("#") or "=" not in stripped:
                continue
            key, _, value = stripped.partition("=")
            key = key.strip()
            if key in keys and key and not os.getenv(key):
                os.environ[key] = value.strip()
    except Exception:
        # Optional helper; ignore parsing errors
        pass


_ensure_openai_key_from_file()
_load_env_file(
    "battery-env.txt",
    {"BATTERY_DATABASE_URL", "BATTERY_DATABASE_PATH", "BATTERY_DATABASE_AUTH"},
)


class Settings(BaseModel):
    database_url: str = Field(
        default=os.getenv("DATABASE_URL", "sqlite:///./data/ev_charging.db")
    )
    business_timezone: str = Field(
        default=os.getenv("BUSINESS_TIMEZONE", "Asia/Seoul")
    )
    admin_email: str = Field(default=os.getenv("ADMIN_EMAIL", "admin@demo.dev"))
    admin_password: str = Field(default=os.getenv("ADMIN_PASSWORD", "admin123"))
    admin_token: str = Field(default=os.getenv("ADMIN_TOKEN", "admin-demo-token"))
    auto_seed_sessions: bool = Field(
        default=os.getenv("AUTO_SEED_SESSIONS", "0").lower()
        in {"1", "true", "yes", "on"}
    )
    cors_origins: list[str] = Field(
        default_factory=lambda: [
            origin.strip()
            for origin in os.getenv("CORS_ORIGINS", "").split(",")
            if origin.strip()
        ]
    )
    # Plate recognition mode:
    # - gptapi : call OpenAI Responses API directly
    # - http   : forward the uploaded image to an external HTTP endpoint
    plate_service_mode: str = Field(
        default=os.getenv("PLATE_SERVICE_MODE", "gptapi").lower()
    )
    plate_service_endpoint: str = Field(
        default=os.getenv(
            "PLATE_SERVICE_URL", "http://localhost:8001/v1/recognize"
        )
    )
    plate_openai_model: str = Field(
        default=os.getenv("PLATE_OPENAI_MODEL", "gpt-5-mini")
    )
    plate_openai_prompt: str = Field(
        default=os.getenv(
            "PLATE_OPENAI_PROMPT",
            (
                "Read only the license plate number from the image. "
                "Return just the plate text; keep any hyphen or dash characters."
                "번호판은 한국 번호판입니다. 숫자와 한글만 포함되어있읍니다 "
                "출력은 번호판 텍스트만 한 줄로 적으세요. 앞뒤에 따옴표, 괄호, 대시(-), 공백, 설명을 추가하지 마세요. 번호판에 실제로 포함된 문자만 그대로 적고 다른 것은 아무것도 쓰지 마세요."
            ),
        )
    )
    openai_api_key: str = Field(default=os.getenv("OPENAI_API_KEY", ""))
    battery_rtdb_url: str = Field(
        default=os.getenv(
            "BATTERY_DATABASE_URL",
            os.getenv("FIREBASE_DATABASE_URL", ""),
        )
    )
    battery_rtdb_path: str = Field(
        default=os.getenv("BATTERY_DATABASE_PATH", "/car-battery-now")
    )
    battery_rtdb_auth: str = Field(
        default=os.getenv("BATTERY_DATABASE_AUTH", "")
    )


@lru_cache(1)
def get_settings() -> Settings:
    return Settings()
