"""
tindex.main — Application server orchestrator.

Creates the aiohttp web application, connects the Telegram client,
sets up Jinja2 template rendering, and runs the HTTP server.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import logging
import pathlib

import aiohttp_jinja2
import jinja2
from aiohttp import web

from .config import api_hash, api_id, host, port, session_string
from .routes import setup_routes
from .telegram import Client
from .views import Views

# ──── LOGGING ──── #

log = logging.getLogger(__name__)


# ──── INDEXER ──── #

class Indexer:
    """
    Main application class.

    Manages the lifecycle of the Telegram client and aiohttp server.
    """

    TEMPLATES_ROOT = pathlib.Path(__file__).parent / "templates"

    def __init__(self) -> None:
        self.server = web.Application()
        self.tg_client = Client(session_string, api_id, api_hash)

    async def startup(self) -> None:
        """Connect to Telegram API, register routes, and configure templates."""
        await self.tg_client.start()
        log.info("Telegram client connected")

        await setup_routes(self.server, Views(self.tg_client))

        loader = jinja2.FileSystemLoader(str(self.TEMPLATES_ROOT))
        aiohttp_jinja2.setup(self.server, loader=loader)

        self.server.on_cleanup.append(self.cleanup)

    async def cleanup(self, *args) -> None:
        """Disconnect the Telegram client on server shutdown."""
        await self.tg_client.disconnect()
        log.info("Telegram client disconnected")

    def run(self) -> None:
        """
        Start the full application.

        Uses aiohttp's built-in runner which handles the event loop
        correctly across Python 3.10+ (no manual get_event_loop needed).
        """
        import asyncio

        async def _start_and_serve():
            await self.startup()
            runner = web.AppRunner(self.server)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()
            log.info("Server listening on http://%s:%d", host, port)

            # Block until cancelled (Ctrl+C)
            try:
                await asyncio.Event().wait()
            finally:
                await runner.cleanup()

        try:
            asyncio.run(_start_and_serve())
        except KeyboardInterrupt:
            log.info("Server stopped by user")
