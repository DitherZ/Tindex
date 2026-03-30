"""
tindex.__main__ — CLI entry point.

Run with:  python -m tindex
Or via:    tindex  (if installed via pip)
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import logging

# ──── MAIN ──── #

def main() -> None:
    """Configure logging and launch the Tindex server."""
    from .config import debug
    from .main import Indexer

    logging.basicConfig(
        level=logging.DEBUG if debug else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Suppress noisy library loggers unless in debug mode
    logging.getLogger("telethon").setLevel(logging.INFO if debug else logging.ERROR)
    logging.getLogger("aiohttp").setLevel(logging.INFO if debug else logging.ERROR)

    Indexer().run()


if __name__ == "__main__":
    main()
