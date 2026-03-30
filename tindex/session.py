"""
tindex.session — Interactive Telethon session string generator.

Run with:  python -m tindex.session

Generates a StringSession for use with the SESSION_STRING env var.
Requires API_ID and API_HASH to be set in .env or environment.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import asyncio
import os
import sys

from dotenv import load_dotenv
from telethon import TelegramClient
from telethon.sessions import StringSession

# ──── GENERATOR ──── #

async def generate() -> None:
    """Interactively authenticate and print a session string."""
    load_dotenv()

    try:
        api_id = int(os.environ["API_ID"])
        api_hash = os.environ["API_HASH"]
    except (KeyError, ValueError):
        print("[ERROR] Set API_ID and API_HASH in .env or environment first")
        print("        Obtain yours at https://my.telegram.org/apps")
        sys.exit(1)

    print("─" * 50)
    print("  Tindex Session String Generator")
    print("─" * 50)
    print()
    print("  Log in with the Telegram account that has")
    print("  access to the channel/chat you want to index.")
    print()

    async with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_string = client.session.save()
        print()
        print("─" * 50)
        print("  Your session string (add to .env as SESSION_STRING):")
        print("─" * 50)
        print()
        print(session_string)
        print()


# ──── CLI ENTRY ──── #

if __name__ == "__main__":
    asyncio.run(generate())
