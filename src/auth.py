import os
import time
import uuid
import json
import urllib.request
import urllib.error
from typing import Optional, Dict
import jwt

JWT_SECRET = os.environ.get("JWT_SECRET", "pepeland_waypoints_jwt_secret_change_me_999")
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_SECONDS = 86400 * 7  # 7 days

# In-memory storage for auth handshakes: nonce -> {"created_at": timestamp, "username": username}
active_nonces: Dict[str, dict] = {}


def generate_nonce(username: str) -> str:
    # Cleanup expired nonces (> 120s)
    now = time.time()
    expired = [k for k, v in active_nonces.items() if now - v.get("created_at", 0) > 120]
    for k in expired:
        active_nonces.pop(k, None)

    nonce = uuid.uuid4().hex
    active_nonces[nonce] = {
        "created_at": now,
        "username": username.lower()
    }
    return nonce


def verify_mojang_session(username: str, server_id: str) -> Optional[dict]:
    """
    Calls https://sessionserver.mojang.com/session/minecraft/hasJoined?username=...&serverId=...
    Returns {'id': 'uuid_without_hyphens', 'name': 'Username'} if verified, else None.
    """
    clean_username = username.strip()
    clean_server_id = server_id.strip()
    url = f"https://sessionserver.mojang.com/session/minecraft/hasJoined?username={clean_username}&serverId={clean_server_id}"

    try:
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "PepelandWaypoints/1.0"}
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status == 200:
                data = json.loads(resp.read().decode("utf-8"))
                raw_id = data.get("id")
                if raw_id:
                    # Format UUID with hyphens standard
                    if len(raw_id) == 32:
                        formatted_uuid = f"{raw_id[0:8]}-{raw_id[8:12]}-{raw_id[12:16]}-{raw_id[16:20]}-{raw_id[20:32]}"
                    else:
                        formatted_uuid = raw_id
                    return {
                        "uuid": formatted_uuid,
                        "raw_uuid": raw_id,
                        "name": data.get("name", username)
                    }
    except Exception as e:
        print(f"[Auth] Error verifying session with Mojang: {e}")
        return None

    return None


def create_token(player_uuid: str, username: str) -> str:
    payload = {
        "sub": player_uuid,
        "name": username,
        "iat": int(time.time()),
        "exp": int(time.time()) + JWT_EXPIRATION_SECONDS
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except Exception:
        return None
