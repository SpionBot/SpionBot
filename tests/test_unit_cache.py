import asyncio

from utils.cache import ImageCache


def test_get_cached_image_id_reads_db_and_memory(fake_pool, fake_conn):
    fake_conn.fetchrow_results.append({"file_id": "file123"})
    cache = ImageCache(fake_pool)

    result = asyncio.run(cache.get_cached_image_id("url1", "mode"))
    assert result == "file123"

    fake_conn.fetchrow_results.append({"file_id": "file999"})
    second = asyncio.run(cache.get_cached_image_id("url1", "mode"))
    assert second == "file123"


def test_get_cached_image_id_returns_none(fake_pool):
    cache = ImageCache(fake_pool)
    result = asyncio.run(cache.get_cached_image_id("missing", "mode"))
    assert result is None


def test_cache_image_id_writes_db(fake_pool, fake_conn):
    cache = ImageCache(fake_pool)
    asyncio.run(cache.cache_image_id("url2", "file456", "mode"))
    assert cache.memory_cache["url2"] == "file456"
    assert fake_conn.executed


def test_cleanup_cache_clears_large_memory(fake_pool, fake_conn):
    cache = ImageCache(fake_pool)
    for i in range(1001):
        cache.memory_cache[f"url{i}"] = f"file{i}"

    asyncio.run(cache.cleanup_cache())
    assert cache.memory_cache == {}
    assert fake_conn.executed
