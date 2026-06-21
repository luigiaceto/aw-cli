"""Shared runtime state for the local web interface."""

import os
from secrets import token_urlsafe
from typing import Any

from aw_web.web.db import WebDatabase


HOST = os.environ.get("AW_WEB_HOST", "127.0.0.1")
PORT = int(os.environ.get("AW_WEB_PORT", "8765"))
DB = WebDatabase()
CSRF_TOKEN = token_urlsafe(32)
STREAMS: dict[str, dict[str, Any]] = {}
CURRENT_PROVIDER: str = ""
