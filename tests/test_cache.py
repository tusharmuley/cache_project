import time

from concurrent.futures import ThreadPoolExecutor
from threading import Lock

import pytest

from app.cache import UserCache


def test_cache_hit(monkeypatch):

    calls = []

    def fake_db(user_id):
        calls.append(user_id)
        return {"id": user_id, "name": "Tushar"}

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        fake_db
    )

    cache = UserCache()

    cache.get_user(1)
    cache.get_user(1)

    assert len(calls) == 1
    assert cache.stats()["cache_hits"] == 1


def test_cache_miss(monkeypatch):

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        lambda user_id: {"id": user_id}
    )

    cache = UserCache()

    result = cache.get_user(1)

    assert result["id"] == 1
    assert cache.stats()["cache_misses"] == 1


def test_expiration(monkeypatch):

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        lambda user_id: {"id": user_id}
    )

    cache = UserCache(ttl=0.1)

    cache.get_user(1)

    time.sleep(0.15)

    cache.get_user(1)

    assert cache.stats()["database_calls"] == 2


def test_lru_eviction(monkeypatch):

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        lambda user_id: {"id": user_id}
    )

    cache = UserCache(max_size=2)

    cache.get_user(1)
    cache.get_user(2)

    # Make user 1 recently used
    cache.get_user(1)

    # User 2 should be evicted
    cache.get_user(3)

    assert list(cache.cache.keys()) == [1, 3]


def test_failed_lookup(monkeypatch):

    def failed_db(user_id):
        raise ValueError("Database failed")

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        failed_db
    )

    cache = UserCache()

    with pytest.raises(ValueError):
        cache.get_user(99)

    assert 99 not in cache.cache


def test_concurrent_same_key(monkeypatch):

    calls = []
    calls_lock = Lock()

    def slow_db(user_id):

        with calls_lock:
            calls.append(user_id)

        time.sleep(0.2)

        return {"id": user_id, "name": "Tushar"}

    monkeypatch.setattr(
        "app.cache.fetch_user_from_database",
        slow_db
    )

    cache = UserCache()

    with ThreadPoolExecutor(max_workers=20) as executor:

        results = list(
            executor.map(cache.get_user, [1] * 20)
        )

    assert len(calls) == 1
    assert len(results) == 20