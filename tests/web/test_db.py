from aw_web.anime import Anime
from aw_web.web.db import WebDatabase


def test_new_watch_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_watch_item(provider="animeunity", anime_data=anime.to_dict())

    item = db.find_watch_item("animeunity", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert item["last_episode"] == "12"


def test_history_does_not_create_watch_item(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_history_item(
        provider="animeunity",
        anime_data=anime.to_dict(),
        current_episode="3",
    )

    assert db.find_history_item("animeunity", "test-ref")["current_episode"] == "3"
    assert db.find_watch_item("animeunity", "test-ref") is None


def test_favorite_item_starts_with_no_progress(tmp_path):
    db = WebDatabase(tmp_path / "web.sqlite3")
    anime = Anime("Test Anime", "test-ref", curr_ep="12", last_ep="12")

    db.upsert_favorite_item(provider="animeunity", anime_data=anime.to_dict())

    item = db.find_favorite_item("animeunity", "test-ref")

    assert item is not None
    assert item["current_episode"] == "0"
    assert item["last_episode"] == "12"
