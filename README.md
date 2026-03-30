[![Tindex](https://see.fontimg.com/api/rf5/woqxz/Njg2Zjc5ZjkzNjUwNGM4Nzk1NzdhNzM5ZTA3YzRmNjEudHRm/VElOREVY/nextf-games-bold-italic.png?r=fs&h=83&w=1500&fg=FFF5F5&bg=FFFFFF&tb=1&s=55)](https://www.fontspace.com/category/futuristic)

> **Modernized fork of [NEOIR/Tindex](https://github.com/NEOIR/Tindex)** — Stream media from Telegram chats via web browser and VLC player.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue?style=for-the-badge)](https://python.org)
[![License: GPL v3](https://img.shields.io/badge/license-GPLv3-orange?style=for-the-badge)](LICENSE)

---

## What's New in v2

| Area | Before (v1) | After (v2) |
|---|---|---|
| **Python** | 3.6–3.9 | 3.10–3.13+ |
| **Packaging** | `requirements.txt` only | `pyproject.toml` (PEP 621) |
| **Jinja2** | `jinja2.Markup` (removed in 3.1) | `markupsafe.Markup` |
| **Pillow** | `draw.textsize()` (removed in 10+) | `draw.textbbox()` |
| **asyncio** | `get_event_loop()` (deprecated) | `asyncio.run()` |
| **Config** | Raw `os.environ` + committed `.env` | `python-dotenv` + `.env.example` |
| **Error handling** | Bare `except:` everywhere | Typed `except Exception:` |
| **Entry point** | `os.system("pip3 install ...")` | Proper `[project.scripts]` |
| **UI** | Tailwind CSS v1 (light theme) | Tailwind CSS v3 (dark theme) |
| **Dead code** | `doodstream` dep, `botCode.py` | Removed |
| **Deployment** | Repl.it only | Docker, pip, manual |

---

## Quick Start

### 1. Install

```bash
# From source
git clone https://github.com/DitherZ/tindex.git
cd tindex
pip install .

# With the optional cryptg accelerator
pip install ".[fast]"
```

### 2. Configure

```bash
cp .env.example .env
# Edit .env with your values
```

You need:

| Variable | Source |
|---|---|
| `API_ID` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `API_HASH` | [my.telegram.org/apps](https://my.telegram.org/apps) |
| `INDEXING_CHAT` | Your channel/group chat ID |
| `SESSION_STRING` | Generate with `python -m tindex.session` |

### 3. Generate Session String

```bash
python -m tindex.session
```

Log in with the Telegram account that has access to your target channel/chat.

### 4. Run

```bash
# Via module
python -m tindex

# Or via entry point (if pip-installed)
tindex
```

Server starts on `http://0.0.0.0:8080` by default.

---

## Docker

```bash
docker build -t tindex .
docker run -d --env-file .env -p 8080:8080 tindex
```

---

## Development

```bash
pip install ".[dev]"
ruff check tindex/
mypy tindex/
```

---

## Project Structure

```
tindex/
├── __init__.py          # Package metadata
├── __main__.py          # CLI entry point
├── config.py            # Environment config + validation
├── main.py              # Indexer server orchestrator
├── routes.py            # URL routing + chat alias generation
├── session.py           # Interactive session string generator
├── telegram.py          # Telethon client with range downloads
├── util.py              # Filename + size helpers
├── views.py             # HTTP handlers (index, info, download, etc.)
└── templates/
    ├── header.html      # Shared header (Tailwind v3, dark theme)
    ├── footer.html      # Shared footer
    ├── home.html        # Source selection page
    ├── index.html       # Chat message listing with pagination
    ├── info.html        # File detail + media player
    ├── otg.html         # On-The-Go indexing form
    └── playlistCreator.html  # M3U8 playlist generator
```

---

## Credits

- Original **tg-index** by [@odysseusmax](https://github.com/odysseusmax/tg-index)
- **TgindexPro** fork by [@rayanfer32](https://github.com/rayanfer32/TgindexPro)
- **Tindex** fork by [@NEOIR](https://github.com/NEOIR/Tindex)
- **v2 modernization** by Blackflame (DitherZ)

## License

[GNU General Public License v3.0](LICENSE)
