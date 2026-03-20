"""Load and validate Twitter API credentials from environment."""
import os
from pathlib import Path

from dotenv import load_dotenv

_env_path = Path(__file__).resolve().parent / ".env"
load_dotenv(_env_path)


def get_bearer_token() -> str | None:
    """Return BEARER_TOKEN from environment, or None if not set."""
    return os.getenv("BEARER_TOKEN") or None


def validate_config() -> tuple[bool, str]:
    """Validate that required credentials are present."""
    token = get_bearer_token()
    if not token or not token.strip():
        return False, (
            "BEARER_TOKEN is not set. Copy .env.example to .env and add your "
            "Twitter API Bearer Token from https://developer.twitter.com"
        )
    return True, ""
