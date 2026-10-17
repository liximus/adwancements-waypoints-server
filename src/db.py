import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv

load_dotenv()

redis_url = os.environ.get(
    "UPSTASH_REDIS_REST_URL",
    "https://brave-mastiff-216319.upstash.io"
)
redis_token = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN",
    "gQAAAAAAA0z_AAIgcDFlN2UxZmJmNGE1YjM0MmEzOTg0YjJjMGQ3ZTU0YzJkNQ"
)

from upstash_redis import Redis

redis = Redis(url=redis_url, token=redis_token)


def read(space: str, key: str) -> dict:
    raw = redis.hget(space, key)
    if raw:
        return json.loads(raw)
    return {}


def read_batch(space: str, keys: List[str]) -> Dict[str, dict]:
    if not keys:
        return {}
    results = {}
    try:
        raw_values = redis.hmget(space, *keys)
        for k, v in zip(keys, raw_values):
            if v:
                results[k] = json.loads(v)
            else:
                results[k] = {}
    except Exception:
        for k in keys:
            results[k] = read(space, k)
    return results


def read_all_from_space(space: str) -> List[dict]:
    raw = redis.hgetall(space)
    if raw:
        arr = []
        for _, j in raw.items():
            if isinstance(j, str):
                arr.append(json.loads(j))
            elif isinstance(j, dict):
                arr.append(j)
        return arr
    return []


def read_all_keys_from_space(space: str) -> List[str]:
    raw = redis.hgetall(space)
    if raw:
        return list(raw.keys())
    return []


def write(space: str, key: str, payload: dict) -> bool:
    dump = json.dumps(payload, ensure_ascii=False)
    redis.hset(space, key, dump)
    return True


def delete(space: str, key: str):
    redis.hdel(space, key)


def set_add(key: str, member: str):
    redis.sadd(key, member)


def set_remove(key: str, member: str):
    redis.srem(key, member)


def set_members(key: str) -> List[str]:
    raw = redis.smembers(key)
    if not raw:
        return []
    return [str(m) for m in raw]


def clearAll():
    redis.flushdb()
