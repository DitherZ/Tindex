"""
tindex.util — Shared utility functions for filename formatting and size display.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

# ──── FILE NAME ──── #

def get_file_name(message) -> str:
    """Extract a display-safe filename from a Telethon Message."""
    if message.file.name:
        return message.file.name.replace("\n", " ")
    ext = message.file.ext or ""
    return f"{message.date.strftime('%Y-%m-%d_%H:%M:%S')}{ext}"


# ──── HUMAN-READABLE SIZE ──── #

def get_human_size(num: int | float) -> str:
    """Convert byte count to a human-readable string (KiB, MiB, etc.)."""
    base = 1024.0
    suffixes = ["B", "KiB", "MiB", "GiB", "TiB", "PiB", "EiB", "ZiB", "YiB"]
    for unit in suffixes:
        if abs(num) < base:
            return f"{round(num, 2)} {unit}"
        num /= base
    return f"{round(num, 2)} YiB"
