import json
import os
from typing import Any, Dict, List, Optional
from dotenv import load_dotenv
import requests

load_dotenv()

redis_url = os.environ.get(
    "UPSTASH_REDIS_REST_URL",
    "https://brave-mastiff-216319.upstash.io"
).rstrip("/")

redis_token = os.environ.get(
    "UPSTASH_REDIS_REST_TOKEN",
    "gQAAAAAAA0z_AAIgcDFlN2UxZmJmNGE1YjM0MmEzOTg0YjJjMGQ3ZTU0YzJkNQ"
)


def _execute(command: List[Any]) -> Any:
    headers = {
        "Authorization": f"Bearer {redis_token}",
        "User-Agent": "PepelandWaypoints/2.0",
        "Connection": "close"
    }
    resp = requests.post(
        redis_url,
        json=command,
        headers=headers,
        timeout=10
    )
    if resp.status_code != 200:
        raise RuntimeError(f"Upstash HTTP {resp.status_code}: {resp.text}")
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Upstash error: {data['error']}")
    return data.get("result")


def read(space: str, key: str) -> dict:
    raw = _execute(["HGET", space, key])
    if raw:
        if isinstance(raw, dict):
            return raw
        return json.loads(raw)
    return {}


def read_batch(space: str, keys: List[str]) -> Dict[str, dict]:
    if not keys:
        return {}
    results = {}
    try:
        raw_values = _execute(["HMGET", space, *keys])
        for k, v in zip(keys, raw_values):
            if v:
                results[k] = json.loads(v) if isinstance(v, str) else v
            else:
                results[k] = {}
    except Exception:
        for k in keys:
            results[k] = read(space, k)
    return results


def read_all_from_space(space: str) -> List[dict]:
    raw_vals = _execute(["HVALS", space])
    if raw_vals:
        arr = []
        for v in raw_vals:
            if isinstance(v, str):
                try:
                    arr.append(json.loads(v))
                except Exception:
                    pass
            elif isinstance(v, dict):
                arr.append(v)
        return arr
    return []


def read_all_keys_from_space(space: str) -> List[str]:
    raw_keys = _execute(["HKEYS", space])
    if raw_keys:
        return [str(k) for k in raw_keys]
    return []


def write(space: str, key: str, payload: dict) -> bool:
    dump = json.dumps(payload, ensure_ascii=False)
    _execute(["HSET", space, key, dump])
    return True


def delete(space: str, key: str):
    _execute(["HDEL", space, key])


def set_add(key: str, member: str):
    _execute(["SADD", key, member])


def set_remove(key: str, member: str):
    _execute(["SREM", key, member])


def set_members(key: str) -> List[str]:
    raw = _execute(["SMEMBERS", key])
    if not raw:
        return []
    return [str(m) for m in raw]


def clearAll():
    _execute(["FLUSHDB"])
