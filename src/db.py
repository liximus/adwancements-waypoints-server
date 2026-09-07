import json
import os
from typing import Any, Optional
from dotenv import load_dotenv
from upstash_redis import Redis

load_dotenv()

redis_url = os.getenv("UPSTASH_REDIS_REST_URL")
redis_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")

if not redis_url or not redis_token:
    # В локальной разработке без .env выводим предупреждение
    print("[WARNING] Upstash Redis credentials not found in environment!")

redis = Redis(url=redis_url or "", token=redis_token or "")


def read(space: str, key: str) -> Optional[dict]:
    raw = redis.hget(space, key)
    if raw:
        try:
            return json.loads(raw)
        except (json.JSONDecodeError, TypeError):
            return None
    return None


def read_all_from_space(space: str) -> list[dict]:
    raw = redis.hgetall(space)
    if not raw:
        return []

    result = []
    for key, val in raw.items():
        try:
            item = json.loads(val)
            if isinstance(item, dict):
                if "id" not in item:
                    item["id"] = key
                result.append(item)
        except (json.JSONDecodeError, TypeError):
            continue
    return result


def read_all_keys_from_space(space: str) -> list[str]:
    keys = redis.hkeys(space)
    return keys or []


def write(space: str, key: str, payload: dict) -> bool:
    dump = json.dumps(payload, ensure_ascii=False)
    redis.hset(space, key, dump)
    return True


def delete(space: str, key: str) -> bool:
    count = redis.hdel(space, key)
    return bool(count and count > 0)


def clear_all():
    redis.flushdb()
