import json
from datetime import datetime, timedelta, timezone

from aw_web.anime import Anime
from aw_web.web.db import WebDatabase
from aw_web.web.watchlist_refresh import (
    db_timestamp,
    refresh_watchlist_availability,
    should_refresh_watch_item,
)


def test_should_refresh_watch_item_after_six_hours():
    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    item = {"episodes_checked_at": db_timestamp(now - timedelta(hours=6))}

    assert should_refresh_watch_item(item, now)


def test_should_not_refresh_watch_item_before_six_hours():
    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    item = {"episodes_checked_at": db_timestamp(now - timedelta(hours=5, minutes=59))}

    assert not should_refresh_watch_item(item, now)


def test_refresh_watchlist_availability_updates_episode_count(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    anime.update_episodes({"8": "episode-8"})
    db.upsert_watch_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="8",
    )

    class FakeProvider:
        def info_anime(self, anime: Anime) -> None:
            anime.last_ep = "9"

        def episodes(self, anime: Anime) -> None:
            anime.update_episodes({"8": "episode-8", "9": "episode-9"})

    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    refresh_watchlist_availability(
        db,
        db.watchlist(),
        provider_factory=lambda provider_name: FakeProvider(),
        now=now,
    )

    item = db.find_watch_item("animeunity", "provider-ref")

    assert item is not None
    assert item["current_episode"] == "8"
    assert item["last_episode"] == "9"
    assert item["episodes_checked_at"] == db_timestamp(now)
    saved_anime = Anime.from_dict(json.loads(str(item["anime_json"])))
    assert saved_anime.has_episode("9")


def test_refresh_watchlist_availability_skips_fresh_items(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    db.upsert_watch_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="8",
    )
    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    db.mark_watch_item_episodes_checked(
        "animeunity",
        "provider-ref",
        db_timestamp(now - timedelta(hours=1)),
    )

    def fail_provider_factory(provider_name):
        raise AssertionError("fresh items should not hit the provider")

    refresh_watchlist_availability(
        db,
        db.watchlist(),
        provider_factory=fail_provider_factory,
        now=now,
    )

    item = db.find_watch_item("animeunity", "provider-ref")
    assert item is not None
    assert item["last_episode"] == "8"


def test_refresh_watchlist_availability_marks_failed_attempt(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Example", "provider-ref", curr_ep="8", last_ep="8")
    db.upsert_watch_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="8",
    )

    class BrokenProvider:
        def info_anime(self, anime: Anime) -> None:
            raise RuntimeError("provider down")

        def episodes(self, anime: Anime) -> None:
            raise AssertionError("episodes should not be called")

    now = datetime(2026, 7, 2, 12, 0, tzinfo=timezone.utc)
    refresh_watchlist_availability(
        db,
        db.watchlist(),
        provider_factory=lambda provider_name: BrokenProvider(),
        now=now,
    )

    item = db.find_watch_item("animeunity", "provider-ref")
    assert item is not None
    assert item["last_episode"] == "8"
    assert item["episodes_checked_at"] == db_timestamp(now)
