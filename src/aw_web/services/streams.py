"""Short-lived playback stream sessions."""

from __future__ import annotations

import time
from uuid import uuid4

from aw_web.anime import Anime
from aw_web.services.playback import validate_media_url
from aw_web.services.providers import get_provider
from aw_web.web.state import STREAMS
from aw_web.web.utils import anime_from_json, anime_to_json


STREAM_TTL_SECONDS = 2 * 60 * 60
MAX_STREAMS = 200


def stream_token(provider_name: str, anime: Anime, episode_num: str) -> str:
    prune_streams()
    token = uuid4().hex
    STREAMS[token] = {
        "provider": provider_name,
        "anime": anime_to_json(anime),
        "episode": episode_num,
        "url": "",
        "urls": [],
        "created_at": time.time(),
    }
    return token


def prune_streams(now: float | None = None) -> None:
    now = now or time.time()
    expired = [
        token
        for token, data in STREAMS.items()
        if now - float(data.get("created_at") or 0) > STREAM_TTL_SECONDS
    ]
    for token in expired:
        STREAMS.pop(token, None)

    if len(STREAMS) <= MAX_STREAMS:
        return

    oldest = sorted(
        STREAMS,
        key=lambda token: float(STREAMS[token].get("created_at") or 0),
    )
    for token in oldest[: len(STREAMS) - MAX_STREAMS]:
        STREAMS.pop(token, None)


def stream_context(token: str) -> tuple[str, Anime, Anime.Episode]:
    prune_streams()
    data = STREAMS.get(token)
    if not data:
        raise RuntimeError("Sessione video scaduta. Riapri l'episodio dalla pagina anime.")
    provider_name = data["provider"]
    anime = anime_from_json(data["anime"])
    episode_num = data["episode"]
    if not anime.has_episode(episode_num):
        provider = get_provider(provider_name)
        provider.episodes(anime)
        data["anime"] = anime_to_json(anime)
    return provider_name, anime, anime.episode(episode_num)


def resolve_episode_urls(token: str, *, refresh: bool = False) -> tuple[list[str], dict[str, str]]:
    data = STREAMS.get(token)
    if data and not refresh:
        provider_name = data["provider"]
        cached_urls = data.get("urls")
        if isinstance(cached_urls, list) and cached_urls:
            urls = [validate_media_url(str(url)) for url in cached_urls]
            selected_url = str(data.get("url") or "")
            if selected_url in urls:
                urls = [selected_url] + [url for url in urls if url != selected_url]
            return urls, dict(get_provider(provider_name).Client.headers)
        if data.get("url"):
            return [validate_media_url(str(data["url"]))], dict(get_provider(provider_name).Client.headers)

    provider_name, anime, episode = stream_context(token)
    provider = get_provider(provider_name)
    urls = []
    seen = set()
    for raw_url in provider.episode_links(anime, episode):
        try:
            url = validate_media_url(str(raw_url))
        except RuntimeError:
            continue
        if url not in seen:
            seen.add(url)
            urls.append(url)
    if not urls:
        raise RuntimeError("Nessun URL video valido trovato.")
    if data is not None:
        data["urls"] = urls
        data["url"] = urls[0]
    return urls, dict(provider.Client.headers)


def resolve_episode_url(token: str) -> tuple[str, dict[str, str]]:
    urls, headers = resolve_episode_urls(token)
    return urls[0], headers
