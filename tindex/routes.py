"""
tindex.routes — URL routing and chat alias generation.

Generates randomized alias IDs for indexed chats and registers
all aiohttp route handlers from the Views class.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import logging
import random
import string

from aiohttp import web

from .config import alias_ids, chat_ids, index_settings

# ──── LOGGING ──── #

log = logging.getLogger(__name__)


# ──── ALIAS GENERATION ──── #

def generate_alias_id(chat) -> str:
    """
    Create a unique random alias ID for a Telegram chat.

    The alias is used in URLs instead of exposing the real chat ID.
    Length matches the digit count of the chat's numeric ID.
    """
    chat_id = chat.id
    title = chat.title
    alias_len = len(str(chat_id))

    while True:
        alias_id = "".join(
            random.choices(string.ascii_letters + string.digits, k=alias_len)
        )
        if alias_id in alias_ids:
            continue

        alias_ids.append(alias_id)
        chat_ids.append({
            "chat_id": chat_id,
            "alias_id": alias_id,
            "title": title,
        })
        return alias_id


# ──── ROUTE SETUP ──── #

async def setup_routes(app: web.Application, handler) -> None:
    """
    Register all HTTP routes and index configured chats.

    Iterates through Telegram dialogs based on index_settings
    and generates alias IDs for each qualifying chat.
    """
    h = handler
    client = h.client
    p = r"/{chat:[^/]+}"

    routes = [
        web.get("/", h.home),
        web.post("/otg", h.dynamic_view),
        web.get("/otg", h.otg_view),
        web.get("/pc", h.playlist_creator),
        # JSON API for infinite scroll
        web.get(p + r"/api/messages", h.api_messages),
        web.get(p, h.index),
        web.get(p + r"/logo", h.logo),
        web.get(p + r"/{id:\d+}/view", h.info),
        web.get(p + r"/{id:\d+}/download", h.download_get),
        web.get(p + r"/{id:\d+}/thumbnail", h.thumbnail_get),
        # Routes that work without an alias ID (single-chat shortcut)
        web.get(r"/{id:\d+}/view", h.info),
        web.get(r"/{id:\d+}/download", h.download_get),
        web.view(r"/{wildcard:.*}", h.wildcard),
    ]

    index_all = index_settings["index_all"]
    index_private = index_settings["index_private"]
    index_group = index_settings["index_group"]
    index_channel = index_settings["index_channel"]
    exclude_chats = index_settings["exclude_chats"]
    include_chats = index_settings["include_chats"]

    if index_all:
        async for chat in client.iter_dialogs():
            alias_id = None

            if chat.id in exclude_chats:
                continue

            if chat.is_user:
                if index_private:
                    alias_id = generate_alias_id(chat)
            elif chat.is_channel:
                if index_channel:
                    alias_id = generate_alias_id(chat)
            else:
                if index_group:
                    alias_id = generate_alias_id(chat)

            if not alias_id:
                continue

            log.debug("Index added for %d :: %s at /%s", chat.id, chat.title, alias_id)
    else:
        for chat_id in include_chats:
            try:
                chat = await client.get_entity(chat_id)
            except Exception:
                log.error("Failed to resolve chat ID %d", chat_id, exc_info=True)
                continue
            alias_id = generate_alias_id(chat)
            log.debug("Index added for %d :: %s at /%s", chat.id, chat.title, alias_id)

    app.add_routes(routes)
