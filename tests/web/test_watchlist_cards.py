from aw_web.anime import Anime
from aw_web.web.components import watch_card
from aw_web.web.utils import anime_to_json, available_last_episode, has_new_episode, next_playable_episode


def test_watch_card_uses_latest_episode_for_display():
    saved_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="10", last_ep="10")
    saved_anime.update_episodes({"10": "old-episode"})
    latest_anime = Anime("Gals Can't Be Kind to Otaku!?", "anime-ref", curr_ep="11", last_ep="11")
    latest_anime.update_episodes({"11": "new-episode"})
    item = {
        "id": 1,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "10",
        "last_episode": "10",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [latest_anime])

    assert has_new_episode(item, [latest_anime])
    assert available_last_episode(item, [latest_anime]) == "11"
    assert next_playable_episode(item, [latest_anime]) == "11"
    assert "Nuovo episodio" in html
    assert "<strong>10</strong> / 11" in html
    assert 'name="episode" value="11"' in html


def test_watch_card_resume_keeps_current_episode_when_no_next_exists():
    saved_anime = Anime("Example", "anime-ref", curr_ep="12", last_ep="12")
    saved_anime.update_episodes({"1": "episode-1", "12": "episode-12"})
    item = {
        "id": 1,
        "provider": "animeunity",
        "name": saved_anime.name,
        "ref": saved_anime.ref,
        "current_episode": "12",
        "last_episode": "12",
        "cover_url": "",
        "anime_json": anime_to_json(saved_anime),
    }

    html = watch_card(item, [])

    assert next_playable_episode(item, []) == "12"
    assert 'name="episode" value="12"' in html
