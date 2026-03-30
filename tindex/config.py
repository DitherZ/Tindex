"""
tindex.config — Environment-driven configuration with validation.

Loads settings from .env file (via python-dotenv) and environment variables.
All required values are validated at import time with clear error messages.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import os
import sys

from dotenv import load_dotenv

# ──── ENV LOADING ──── #

load_dotenv()


# ──── PORT ──── #

try:
    port: int = int(os.environ.get("PORT", "8080"))
except ValueError:
    port = -1

if not 1 <= port <= 65535:
    print("[FATAL] PORT must be an integer between 1 and 65535")
    sys.exit(1)


# ──── TELEGRAM API CREDENTIALS ──── #

try:
    api_id: int = int(os.environ["API_ID"])
    api_hash: str = os.environ["API_HASH"]
except KeyError:
    print("[FATAL] API_ID and API_HASH environment variables are required")
    print("        Obtain yours at https://my.telegram.org/apps")
    sys.exit(1)
except ValueError:
    print("[FATAL] API_ID must be a valid integer")
    sys.exit(1)


# ──── SESSION STRING ──── #

try:
    session_string: str = os.environ["SESSION_STRING"]
except KeyError:
    print("[FATAL] SESSION_STRING environment variable is required")
    print("        Generate one with: python -m tindex.session")
    sys.exit(1)


# ──── INDEXING SETTINGS ──── #

try:
    indexing_chat: int = int(os.environ["INDEXING_CHAT"])
except KeyError:
    print("[FATAL] INDEXING_CHAT environment variable is required")
    sys.exit(1)
except ValueError:
    print("[FATAL] INDEXING_CHAT must be a valid integer (chat ID)")
    sys.exit(1)

index_settings: dict = {
    "index_all": False,
    "index_private": True,
    "index_group": True,
    "index_channel": True,
    "exclude_chats": [],
    "include_chats": [indexing_chat],
    "otg": {
        "enable": True,
        "include_private": True,
        "include_group": True,
        "include_channel": True,
    },
}

otg_settings: dict = index_settings["otg"]
enable_otg: bool = otg_settings["enable"]


# ──── SERVER SETTINGS ──── #

host: str = os.environ.get("HOST", "0.0.0.0")
debug: bool = bool(os.environ.get("DEBUG"))


# ──── RUNTIME STATE ──── #
# Mutable lists populated by routes.setup_routes()

chat_ids: list[dict] = []
alias_ids: list[str] = []
