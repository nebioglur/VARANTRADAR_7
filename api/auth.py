"""Small, fail-closed API token check independent of web framework."""
import hmac
import os


def is_valid_api_token(provided: str, expected: str | None = None) -> bool:
    expected = os.environ.get("API_AUTH_TOKEN", "") if expected is None else expected
    return bool(expected and provided and hmac.compare_digest(provided, expected))
