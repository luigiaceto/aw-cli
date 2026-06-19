"""Watch progress persistence helpers."""

from __future__ import annotations

from aw_web.anime import Anime
from aw_web.services.anilist import get_cover
from aw_web.web.state import DB


def save_watch_progress(provider_name: str, anime: Anime, episode: Anime.Episode) -> None:
    cover = get_cover(anime.anilist_id, anime.name)
    DB.upsert_history_item(
        provider=provider_name,
        anime_data=anime.to_dict(),
        cover_url=cover["cover_url"],
        banner_url=cover["banner_url"],
        current_episode=episode.num,
    )
    if DB.find_watch_item(provider_name, anime.ref):
        DB.upsert_watch_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=cover["cover_url"],
            banner_url=cover["banner_url"],
            current_episode=episode.num,
        )
    if DB.find_favorite_item(provider_name, anime.ref):
        DB.upsert_favorite_item(
            provider=provider_name,
            anime_data=anime.to_dict(),
            cover_url=cover["cover_url"],
            banner_url=cover["banner_url"],
            current_episode=episode.num,
        )
