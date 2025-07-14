"""
Module to manage redis connections, general utilities for
bulk read and write, etc

"""

from datetime import date
from typing import Dict, List, Optional

import redis.asyncio as redis

_redis_client: Optional[redis.Redis] = None


def get_redis_client() -> redis.Redis:
    """
    Returns a singleton async Redis client.

    """
    global _redis_client
    if _redis_client is None:
        _redis_client = redis.Redis.from_url("redis://redis:6379")
    return _redis_client


def index_key(index_date: date) -> str:
    """
    Creates the Redis key for an index snapshot for a given date.
    Example: index:2025-07-13

    """
    return f"index:{index_date.isoformat()}"


def changes_key(changes_date: date) -> str:
    """
    Creates the Redis key for a list of changes for a given date.
    Example: changes:2025-07-13

    """
    return f"changes:{changes_date.isoformat()}"


async def bulk_write(kv_pairs: Dict[str, str]) -> None:
    """
    Bulk write key-value pairs to Redis using pipelining.

    """
    if not kv_pairs:
        return

    client: redis.Redis = get_redis_client()
    async with client.pipeline() as pipe:
        for key, value in kv_pairs.items():
            pipe.set(key, value)
        await pipe.execute()


async def bulk_read(keys: List[str]) -> Dict[str, Optional[bytes]]:
    """
    Bulk read keys from Redis using pipelining.
    Returns a dict mapping keys to their values (or None if not found).

    """
    if not keys:
        return {}

    client: redis.Redis = get_redis_client()
    async with client.pipeline() as pipe:
        for key in keys:
            pipe.get(key)
        results = await pipe.execute()

    return dict(zip(keys, results))
