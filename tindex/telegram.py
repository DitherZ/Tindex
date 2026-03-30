"""
tindex.telegram — Telethon client wrapper with chunked download support.

Provides a thin Client subclass that adds range-based file download
streaming for serving media over HTTP with byte-range support.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import asyncio
import logging
import math

from telethon import TelegramClient, utils
from telethon.sessions import StringSession

# ──── LOGGING ──── #

log = logging.getLogger(__name__)


# ──── CLIENT ──── #

class Client(TelegramClient):
    """Extended TelegramClient with HTTP range-download streaming."""

    def __init__(self, session_string: str, *args, **kwargs) -> None:
        super().__init__(StringSession(session_string), *args, **kwargs)

    async def download(self, file, file_size: int, offset: int, limit: int):
        """
        Async generator yielding file chunks for a byte range.

        Args:
            file:      Telethon media object to download.
            file_size: Total size in bytes.
            offset:    Start byte (inclusive).
            limit:     End byte (exclusive).
        """
        part_size_kb = utils.get_appropriated_part_size(file_size)
        part_size = int(part_size_kb * 1024)
        first_part_cut = offset % part_size
        first_part = math.floor(offset / part_size)
        last_part_cut = part_size - (limit % part_size)
        last_part = math.ceil(limit / part_size)
        part_count = math.ceil(file_size / part_size)
        part = first_part

        try:
            async for chunk in self.iter_download(
                file,
                offset=first_part * part_size,
                request_size=part_size,
            ):
                if part == first_part:
                    yield chunk[first_part_cut:]
                elif part == last_part:
                    yield chunk[:last_part_cut]
                else:
                    yield chunk

                log.debug("Part %d/%d (total %d) served", part, last_part, part_count)
                part += 1

            log.debug("File serve completed")

        except (GeneratorExit, StopAsyncIteration, asyncio.CancelledError):
            log.debug("File serve interrupted")
            raise
        except Exception:
            log.debug("File serve errored", exc_info=True)
