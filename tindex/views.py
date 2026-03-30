"""
tindex.views — HTTP request handlers for the Telegram index web UI.

Handles page rendering, file info display, media streaming with
byte-range support, thumbnail generation, and OTG indexing.
"""

# ──── IMPORTS ──── #

from __future__ import annotations

import io
import json
import logging
import random

import aiohttp_jinja2
from aiohttp import web
from markupsafe import Markup
from PIL import Image, ImageDraw
from telethon.tl import types
from telethon.tl.custom import Message
from telethon.tl.types import Channel, Chat, User

from .config import chat_ids, enable_otg, otg_settings
from .util import get_file_name, get_human_size

# ──── LOGGING ──── #

log = logging.getLogger(__name__)


# ──── PILLOW HELPERS ──── #

def _measure_text(draw: ImageDraw.ImageDraw, text: str) -> tuple[int, int]:
    """
    Measure text dimensions using the modern Pillow API.

    Pillow 10+ removed draw.textsize() in favour of draw.textbbox().
    This helper returns (width, height) compatible with both APIs.
    """
    bbox = draw.textbbox((0, 0), text)
    return bbox[2] - bbox[0], bbox[3] - bbox[1]


def _generate_placeholder(width: int, height: int, label: str = "") -> bytes:
    """Generate a solid-color placeholder PNG with optional centred label."""
    color = tuple(random.randint(0, 255) for _ in range(3))
    im = Image.new("RGB", (width, height), color)

    if label:
        draw = ImageDraw.Draw(im)
        w, h = _measure_text(draw, label)
        draw.text(((width - w) / 2, (height - h) / 2), label, fill="white")

    buf = io.BytesIO()
    im.save(buf, "PNG")
    return buf.getvalue()


# ──── CHAT LOOKUP HELPERS ──── #

def _resolve_chat(alias_id: str) -> dict | None:
    """Find a chat entry by alias ID, or None if not found."""
    matches = [c for c in chat_ids if c["alias_id"] == alias_id]
    return matches[0] if matches else None


def _get_chat_id(req, *, allow_otg: bool = True) -> tuple[str, int]:
    """
    Extract alias_id and numeric chat_id from a request.

    Falls back to OTG mode (raw numeric alias) when allowed.
    Raises HTTPFound('/') on failure.

    Returns:
        (alias_id, chat_id) tuple.
    """
    try:
        alias_id = req.match_info["chat"]
    except KeyError:
        if chat_ids:
            alias_id = chat_ids[0]["alias_id"]
        else:
            raise web.HTTPFound("/") from None

    chat = _resolve_chat(alias_id)
    if chat:
        return alias_id, chat["chat_id"]

    if allow_otg and enable_otg:
        try:
            return alias_id, int(alias_id)
        except ValueError:
            pass

    raise web.HTTPFound("/")


def _build_entry(m, alias_id: str, base_path: str) -> dict | None:
    """Build a result dict from a Telethon message, or None if not displayable."""
    if m.file and not isinstance(m.media, types.MessageMediaWebPage):
        return {
            "file_id": m.id,
            "media": True,
            "thumbnail": f"/{alias_id}/{m.id}/thumbnail",
            "mime_type": m.file.mime_type,
            "insight": get_file_name(m),
            "date": str(m.date),
            "size": m.file.size,
            "human_size": get_human_size(m.file.size),
            "url": f"{base_path}/{m.id}/view",
            "download": f"{base_path}/{m.id}/download",
        }
    elif m.message:
        return {
            "file_id": m.id,
            "media": False,
            "mime_type": "text/plain",
            "insight": m.raw_text[:100],
            "date": str(m.date),
            "size": len(m.raw_text),
            "human_size": get_human_size(len(m.raw_text)),
            "url": f"{base_path}/{m.id}/view",
        }
    return None


# ──── VIEWS ──── #

class Views:
    """HTTP request handlers for the Tindex web interface."""

    def __init__(self, client) -> None:
        self.client = client

    # ──── REDIRECTS ──── #

    async def wildcard(self, req):
        """Catch-all: redirect unknown paths to home."""
        raise web.HTTPFound("/")

    # ──── HOME ──── #

    @aiohttp_jinja2.template("home.html")
    async def home(self, req):
        if len(chat_ids) == 1:
            raise web.HTTPFound(f"{chat_ids[0]['alias_id']}")

        chats = [
            {
                "page_id": chat["alias_id"],
                "name": chat["title"],
                "url": req.rel_url.path + f"/{chat['alias_id']}",
            }
            for chat in chat_ids
        ]
        return {"chats": chats, "otg": enable_otg}

    # ──── OTG (ON-THE-GO) INDEXING ──── #

    @aiohttp_jinja2.template("otg.html")
    async def otg_view(self, req):
        if not enable_otg:
            raise web.HTTPFound("/")
        return_data = {}
        error = req.query.get("e")
        if error:
            return_data["error"] = error
        return return_data

    # ──── PLAYLIST CREATOR ──── #

    @aiohttp_jinja2.template("playlistCreator.html")
    async def playlist_creator(self, req):
        return_data = {}
        error = req.query.get("e")
        if error:
            return_data["error"] = error
        return return_data

    # ──── DYNAMIC OTG VIEW ──── #

    async def dynamic_view(self, req):
        if not enable_otg:
            raise web.HTTPFound("/")

        rel_url = req.rel_url
        include_private = otg_settings["include_private"]
        include_group = otg_settings["include_group"]
        include_channel = otg_settings["include_channel"]

        post_data = await req.post()
        raw_id = post_data.get("id")
        if not raw_id:
            raise web.HTTPFound("/")

        raw_id = raw_id.replace("@", "")

        try:
            chat = await self.client.get_entity(raw_id)
        except Exception as exc:
            log.debug("OTG entity lookup failed: %s", exc, exc_info=True)
            raise web.HTTPFound(
                rel_url.with_query({"e": f"No chat found with username {raw_id}"})
            ) from exc

        if isinstance(chat, User) and not include_private:
            raise web.HTTPFound(
                rel_url.with_query({"e": "Indexing private chats is not supported!"})
            )
        elif isinstance(chat, Channel) and not include_channel:
            raise web.HTTPFound(
                rel_url.with_query({"e": "Indexing channels is not supported!"})
            )
        elif isinstance(chat, Chat) and not include_group:
            raise web.HTTPFound(
                rel_url.with_query({"e": "Indexing group chats is not supported!"})
            )

        log.debug("OTG access: chat %s", chat)
        raise web.HTTPFound(f"/{chat.id}")

    # ──── JSON API FOR INFINITE SCROLL ──── #

    async def api_messages(self, req):
        """Return paginated messages as JSON for infinite scroll."""
        alias_id = req.match_info["chat"]
        chat = _resolve_chat(alias_id)

        if not chat:
            if not enable_otg:
                return web.json_response({"items": [], "has_more": False})
            try:
                chat_id = int(alias_id)
            except ValueError:
                return web.json_response({"items": [], "has_more": False})
        else:
            chat_id = chat["chat_id"]

        try:
            page = max(1, int(req.query.get("page", "1")))
        except ValueError:
            page = 1

        search_query = req.query.get("search", "")
        offset = (page - 1) * 30
        base_path = f"/{alias_id}"

        try:
            kwargs = {"entity": chat_id, "limit": 30, "add_offset": offset}
            if search_query:
                kwargs["search"] = search_query
            messages = (await self.client.get_messages(**kwargs)) or []
        except Exception:
            log.debug("API: failed to get messages", exc_info=True)
            messages = []

        results = []
        for m in messages:
            entry = _build_entry(m, alias_id, base_path)
            if entry:
                results.append(entry)

        return web.json_response({
            "items": results,
            "has_more": len(messages) == 30,
            "page": page,
        })

    # ──── CHAT INDEX ──── #

    @aiohttp_jinja2.template("index.html")
    async def index(self, req):
        alias_id = req.match_info["chat"]
        chat = _resolve_chat(alias_id)

        if not chat:
            if not enable_otg:
                raise web.HTTPFound("/")
            try:
                chat_id = int(alias_id)
                chat_entity = await self.client.get_entity(chat_id)
                chat_name = chat_entity.title
            except Exception:
                raise web.HTTPFound("/") from None
        else:
            chat_id = chat["chat_id"]
            chat_name = chat["title"]

        search_query = req.query.get("search", "")
        base_path = f"/{alias_id}"

        # First page loaded server-side for instant render
        try:
            kwargs = {"entity": chat_id, "limit": 30}
            if search_query:
                kwargs["search"] = search_query
            messages = (await self.client.get_messages(**kwargs)) or []
        except Exception:
            log.debug("Failed to get messages", exc_info=True)
            messages = []

        results = []
        for m in messages:
            entry = _build_entry(m, alias_id, base_path)
            if entry:
                results.append(entry)

        return {
            "item_list": results,
            "has_more": len(messages) == 30,
            "search": search_query,
            "name": chat_name,
            "logo": f"/{alias_id}/logo",
            "title": "Index of " + chat_name,
            "alias_id": alias_id,
            "initial_json": json.dumps(results),
        }

    # ──── FILE INFO ──── #

    @aiohttp_jinja2.template("info.html")
    async def info(self, req):
        file_id = int(req.match_info["id"])
        alias_id, chat_id = _get_chat_id(req)

        try:
            message = await self.client.get_messages(entity=chat_id, ids=file_id)
        except Exception:
            log.debug("Error getting message %d in %d", file_id, chat_id, exc_info=True)
            message = None

        if not message or not isinstance(message, Message):
            log.debug("No valid entry for %d in %d", file_id, chat_id)
            return {
                "found": False,
                "reason": "Entry you are looking for cannot be retrieved!",
            }

        return_val: dict = {}

        # Inline reply buttons
        reply_btns = []
        if message.reply_markup and isinstance(
            message.reply_markup, types.ReplyInlineMarkup
        ):
            for button_row in message.reply_markup.rows:
                btns = []
                for button in button_row.buttons:
                    if isinstance(button, types.KeyboardButtonUrl):
                        btns.append({"url": button.url, "text": button.text})
                reply_btns.append(btns)

        # Media file entry
        if message.file and not isinstance(message.media, types.MessageMediaWebPage):
            file_name = get_file_name(message)
            file_size = message.file.size
            human_file_size = get_human_size(file_size)

            media: dict = {"type": message.file.mime_type}
            if "video/" in message.file.mime_type:
                media["video"] = True
            elif "audio/" in message.file.mime_type:
                media["audio"] = True
            elif "image/" in message.file.mime_type:
                media["image"] = True

            caption = message.raw_text if message.text else ""
            caption_html = str(Markup.escape(caption)).replace("\n", "<br>")

            return_val = {
                "found": True,
                "name": file_name,
                "file_id": file_id,
                "size": file_size,
                "human_size": human_file_size,
                "media": media,
                "caption_html": caption_html,
                "caption": caption,
                "title": f"Download | {file_name} | {human_file_size}",
                "reply_btns": reply_btns,
                "thumbnail": f"/{alias_id}/{file_id}/thumbnail",
                "download_url": f"/{alias_id}/{file_id}/download",
                "page_id": alias_id,
            }

        # Text-only entry
        elif message.message:
            text = message.raw_text
            text_html = str(Markup.escape(text)).replace("\n", "<br>")
            return_val = {
                "found": True,
                "media": False,
                "text": text,
                "text_html": text_html,
                "reply_btns": reply_btns,
                "page_id": alias_id,
            }
        else:
            return_val = {
                "found": False,
                "reason": "Unsupported entry type",
            }

        log.debug("Data for %d in %d returned", file_id, chat_id)
        return return_val

    # ──── CHAT LOGO / PROFILE PHOTO ──── #

    async def logo(self, req):
        alias_id = req.match_info["chat"]
        chat = _resolve_chat(alias_id)

        if not chat:
            if not enable_otg:
                return web.Response(status=403, text="403: Forbidden")
            try:
                chat_id = int(alias_id)
            except ValueError:
                return web.Response(status=403, text="403: Forbidden")
        else:
            chat_id = chat["chat_id"]

        try:
            photo = await self.client.get_profile_photos(chat_id)
        except Exception:
            log.debug("Error getting profile photo for %d", chat_id, exc_info=True)
            photo = None

        if not photo:
            body = _generate_placeholder(160, 160, "No Image")
        else:
            photo = photo[0]
            pos = -1 if req.query.get("big") else int(len(photo.sizes) / 2)
            size = self.client._get_thumb(photo.sizes, pos)

            if isinstance(size, (types.PhotoCachedSize, types.PhotoStrippedSize)):
                body = self.client._download_cached_photo_size(size, bytes)
            else:
                media = types.InputPhotoFileLocation(
                    id=photo.id,
                    access_hash=photo.access_hash,
                    file_reference=photo.file_reference,
                    thumb_size=size.type,
                )
                body = self.client.iter_download(media)

        return web.Response(
            status=200,
            body=body,
            headers={
                "Content-Type": "image/jpeg",
                "Content-Disposition": 'inline; filename="logo.jpg"',
            },
        )

    # ──── FILE DOWNLOAD / STREAMING ──── #

    async def download_get(self, req):
        return await self._handle_download(req)

    async def _handle_download(self, req):
        """Serve a file with proper HTTP byte-range support for streaming."""
        file_id = int(req.match_info["id"])
        alias_id, chat_id = _get_chat_id(req)

        try:
            message = await self.client.get_messages(entity=chat_id, ids=file_id)
        except Exception:
            log.debug("Error getting message %d in %d", file_id, chat_id, exc_info=True)
            message = None

        if not message or not message.file:
            log.debug("No result for %d in %d", file_id, chat_id)
            return web.Response(status=410, text="410: Gone")

        media = message.media
        size = message.file.size
        file_name = get_file_name(message)
        mime_type = message.file.mime_type

        # Determine if this is a range request
        http_range = req.http_range
        range_start = http_range.start
        range_end = http_range.stop

        if range_start is not None:
            # Range request
            offset = range_start
            # HTTP ranges are inclusive on both ends: bytes=0-499 means 500 bytes
            limit = min(range_end + 1, size) if range_end is not None else size

            if offset < 0 or offset >= size or limit > size:
                return web.Response(
                    status=416,
                    text="416: Range Not Satisfiable",
                    headers={"Content-Range": f"bytes */{size}"},
                )

            body = self.client.download(media, size, offset, limit)
            content_length = limit - offset

            log.info(
                "Serving file %d (chat %d) ; Range: %d-%d/%d",
                file_id, chat_id, offset, limit - 1, size,
            )

            return web.Response(
                status=206,
                body=body,
                headers={
                    "Content-Type": mime_type,
                    "Content-Range": f"bytes {offset}-{limit - 1}/{size}",
                    "Content-Length": str(content_length),
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": f'inline; filename="{file_name}"',
                },
            )
        else:
            # Full request (no Range header)
            body = self.client.download(media, size, 0, size)

            log.info("Serving full file %d (chat %d) ; Size: %d", file_id, chat_id, size)

            return web.Response(
                status=200,
                body=body,
                headers={
                    "Content-Type": mime_type,
                    "Content-Length": str(size),
                    "Accept-Ranges": "bytes",
                    "Content-Disposition": f'inline; filename="{file_name}"',
                },
            )

    # ──── THUMBNAIL ──── #

    async def thumbnail_get(self, req):
        file_id = int(req.match_info["id"])
        alias_id = req.match_info["chat"]
        chat = _resolve_chat(alias_id)

        if not chat:
            if not enable_otg:
                return web.Response(status=403, text="403: Forbidden")
            try:
                chat_id = int(alias_id)
            except ValueError:
                return web.Response(status=403, text="403: Forbidden")
        else:
            chat_id = chat["chat_id"]

        try:
            message = await self.client.get_messages(entity=chat_id, ids=file_id)
        except Exception:
            log.debug("Error getting message %d in %d", file_id, chat_id, exc_info=True)
            message = None

        if not message or not message.file:
            log.debug("No result for %d in %d", file_id, chat_id)
            return web.Response(status=410, text="410: Gone")

        if message.document:
            media = message.document
            thumbnails = media.thumbs
            location = types.InputDocumentFileLocation
        else:
            media = message.photo
            thumbnails = media.sizes
            location = types.InputPhotoFileLocation

        if not thumbnails:
            body = _generate_placeholder(160, 90)
        else:
            thumb_pos = int(len(thumbnails) / 2)
            thumbnail = self.client._get_thumb(thumbnails, thumb_pos)

            if not thumbnail or isinstance(thumbnail, types.PhotoSizeEmpty):
                return web.Response(status=410, text="410: Gone")

            if isinstance(thumbnail, (types.PhotoCachedSize, types.PhotoStrippedSize)):
                body = self.client._download_cached_photo_size(thumbnail, bytes)
            else:
                actual_file = location(
                    id=media.id,
                    access_hash=media.access_hash,
                    file_reference=media.file_reference,
                    thumb_size=thumbnail.type,
                )
                body = self.client.iter_download(actual_file)

        return web.Response(
            status=200,
            body=body,
            headers={
                "Content-Type": "image/jpeg",
                "Content-Disposition": 'inline; filename="thumbnail.jpg"',
            },
        )
