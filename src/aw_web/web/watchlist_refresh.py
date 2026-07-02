"""Watchlist episode availability refresh helpers."""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Callable, Protocol

from aw_web import providers
from aw_web.anime import Anime
from aw_web.web.db import WebDatabase


WATCHLIST_REFRESH_INTERVAL = timedelta(hours=6)


class EpisodeAvailabilityProvider(Protocol):
    def info_anime(self, anime: Anime) -> None:
        ...

    def episodes(self, anime: Anime) -> None:
        ...


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def db_timestamp(value: datetime) -> str:
    return value.astimezone(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


def parse_db_timestamp(value: object) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def should_refresh_watch_item(item: dict[str, Any], now: datetime | None = None) -> bool:
    checked_at = parse_db_timestamp(item.get("episodes_checked_at"))
    if checked_at is None:
        return True
    return (now or utc_now()) - checked_at >= WATCHLIST_REFRESH_INTERVAL


def refresh_watchlist_availability(
    db: WebDatabase,
    items: list[dict[str, Any]],
    *,
    provider_factory: Callable[[str], EpisodeAvailabilityProvider],
    now: datetime | None = None,
) -> None:
    checked_at = now or utc_now()
    checked_at_value = db_timestamp(checked_at)
    for item in items:
        provider_name = str(item.get("provider") or "")
        ref = str(item.get("ref") or "")
        if provider_name not in providers.PROVIDERS_AVAILABLE or not ref:
            continue
        if not should_refresh_watch_item(item, checked_at):
            continue

        try:
            provider = provider_factory(provider_name)
            anime = Anime.from_dict(json.loads(str(item["anime_json"])))
            provider.info_anime(anime)
            provider.episodes(anime)
            db.update_watch_item_availability(
                provider=provider_name,
                ref=ref,
                anime_data=anime.to_dict(),
                cover_url=str(item.get("cover_url") or ""),
                banner_url=str(item.get("banner_url") or ""),
                checked_at=checked_at_value,
            )
        except Exception:
            db.mark_watch_item_episodes_checked(provider_name, ref, checked_at_value)
