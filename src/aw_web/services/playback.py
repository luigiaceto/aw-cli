"""Media URL validation and external player launch helpers."""

from __future__ import annotations

import shutil
import subprocess
from ipaddress import ip_address
from pathlib import Path
from urllib.parse import urlparse

from aw_web import utilities as ut


_BLOCKED_HOSTS = {"localhost"}


def validate_media_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        raise RuntimeError("URL video non valido.")
    if parsed.username or parsed.password:
        raise RuntimeError("URL video non valido.")

    hostname = parsed.hostname.lower().rstrip(".")
    if hostname in _BLOCKED_HOSTS or hostname.endswith(".localhost"):
        raise RuntimeError("URL video non consentito.")

    try:
        address = ip_address(hostname)
    except ValueError:
        return url

    if (
        address.is_private
        or address.is_loopback
        or address.is_link_local
        or address.is_multicast
        or address.is_reserved
        or address.is_unspecified
    ):
        raise RuntimeError("URL video non consentito.")
    return url


def open_external_player(url: str, title: str) -> None:
    url = validate_media_url(url)
    player = ut.config_data.get("player", {})
    configured_path = str(player.get("path") or "")
    configured_type = str(player.get("type") or "")
    if configured_type == "mpv" and configured_path and "mpv" in Path(configured_path).name.lower():
        player_path = configured_path
    else:
        player_path = shutil.which("mpv") or ""
    if not player_path:
        raise RuntimeError("Nessun player trovato. Installa mpv o usa il player browser.")

    command = [player_path, url, f"--force-media-title={title}", "--fullscreen", "--keep-open"]
    try:
        subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        raise RuntimeError(f"Impossibile avviare il player esterno: {exc}") from exc
