import os
import re

from dotenv import load_dotenv

load_dotenv()


class ConfigurationError(Exception):
    pass


def gemini_settings() -> tuple[str, str]:
    key = os.getenv("GEMINI_API_KEY", "").strip()
    model = os.getenv("GEMINI_MODEL", "gemini-3.5-flash-lite")
    if not key or not re.fullmatch(r"gemini-[a-z0-9.-]+", model):
        raise ConfigurationError("The analysis provider is not configured.")
    return key, model
