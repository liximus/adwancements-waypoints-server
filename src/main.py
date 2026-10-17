from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Header, status
from pydantic import BaseModel, Field
import src.wp_db as wp_db
import src.auth as auth

app = FastAPI(title="Pepeland Waypoints API", version="2.0.0")


class DisplayInfo(BaseModel):
    title: str
    description: str
    icon: str
    frame: Optional[str] = "task"
    background: Optional[str] = None


class WaypointPayload(BaseModel):
    id: str
    parent: Optional[str] = None
    display: DisplayInfo
    author_uuid: Optional[str] = None
    author_name: Optional[str] = None


class BatchStatusRequest(BaseModel):
    ids: List[str]


class AuthorActionRequest(BaseModel):
    wp_id: str
    author_uuid: Optional[str] = None


class AuthStartRequest(BaseModel):
    username: str


class AuthVerifyRequest(BaseModel):
    username: str
    server_id: str


class ApproveRequest(BaseModel):
    wp_id: str
    new_parent: Optional[str] = None
    edited_wp: Optional[Dict[str, Any]] = None


class DeclineRequest(BaseModel):
    wp_id: str
    reason: Optional[str] = "Отклонено модератором"


class BlockRequest(BaseModel):
    wp_id: str
    reason: Optional[str] = "Отклонено модератором"


class AdminSaveRequest(BaseModel):
    waypoint: Dict[str, Any]


class AdminDeleteRequest(BaseModel):
    wp_id: str


import os

# ------------------ 2-FACTOR ADMIN & MODERATION AUTH ------------------
# Переменная IS_DEBUG (режим отладки):
# True  — (ПО УМОЛЧАНИЮ ДЛЯ ТЕСТОВ) разрешает пиратки, gradlew runClient и любые тестовые ники.
#         Для работы нужен только правильный пароль администратора в панели (pepe2026admin).
# False — БОЕВОЙ РЕЖИМ (ПРОДАКШН): строгая 2FA (пароль + подлинная лицензия Mojang для Kubikov / Allllter).
IS_DEBUG = os.environ.get("IS_DEBUG", "true").lower() in ("true", "1", "yes")

# Пароль администратора (код доступа):
ADMIN_SECRET_KEY = os.environ.get("ADMIN_SECRET_KEY", "pepe2026admin")

# Белый список разрешенных лицензионных аккаунтов (активен при IS_DEBUG = False):
ALLOWED_MODERATOR_NICKNAMES = ["Kubikov", "Allllter"]


def get_current_user_uuid(authorization: Optional[str] = Header(None)) -> Optional[str]:
    """Helper to extract and verify JWT player UUID if present"""
    if not authorization:
        return None
    token = authorization.replace("Bearer ", "").strip()
    payload = auth.decode_token(token)
    if payload and "sub" in payload:
        return payload["sub"]
    return None


import hmac

GENERIC_AUTH_ERROR = "Доступ запрещен."


def verify_moderator(
    authorization: Optional[str] = Header(None),
    x_admin_key: Optional[str] = Header(None),
    x_admin_username: Optional[str] = Header(None),
):
    """
    Проверка прав модератора:
    - При IS_DEBUG = True: режим тестирования (пиратка и runClient разрешены).
      Достаточно ввести правильный пароль в админ-панели.
    - При IS_DEBUG = False: боевая 2FA (лицензия Mojang из белого списка + пароль).
    """
    # ── ФАКТОР 1: Проверка пароля с защитой от тайминг-атак ──
    key_bytes = (x_admin_key or "").strip().encode("utf-8")
    secret_bytes = ADMIN_SECRET_KEY.encode("utf-8")
    valid_password = hmac.compare_digest(key_bytes, secret_bytes)

    # ── ФАКТОР 2: Проверка аккаунта / лицензии ──
    valid_license = False

    if IS_DEBUG:
        # В режиме отладки пиратки и локальные тесты разрешены
        valid_license = True
    else:
        # Боевой режим: строгая проверка токена от серверов Mojang
        if authorization and isinstance(authorization, str) and authorization.startswith("Bearer "):
            token = authorization.replace("Bearer ", "").strip()
            payload = auth.decode_token(token)
            if payload and payload.get("sub"):
                verified_username = payload.get("name", "")
                allowed_lower = [name.strip().lower() for name in ALLOWED_MODERATOR_NICKNAMES]
                if verified_username.strip().lower() in allowed_lower:
                    valid_license = True

    # Единый ответ при любой ошибке (оракул аутентификации закрыт)
    if not (valid_password and valid_license):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=GENERIC_AUTH_ERROR
        )

    return True


@app.get("/")
@app.get("/api")
@app.get("/api/")
@app.get("/api/index")
@app.get("/api/index.py")
def health_check():
    return {
        "status": "ok",
        "service": "pepeland-waypoints"
    }


# ------------------ MOJANG AUTH ENDPOINTS ------------------

@app.post("/auth/start")
def auth_start(req: AuthStartRequest):
    """Generates a random nonce for Minecraft client joinServer handshake"""
    if not req.username or not req.username.strip():
        raise HTTPException(status_code=400, detail="Username is required")
    nonce = auth.generate_nonce(req.username)
    return {"status": "ok", "nonce": nonce}


@app.post("/auth/verify")
def auth_verify(req: AuthVerifyRequest):
    """
    Verifies that client actually joined Mojang session with server_id.
    Issues JWT token valid for 7 days.
    """
    session = auth.verify_mojang_session(req.username, req.server_id)
    if not session:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mojang session verification failed. Ensure you are using a genuine Minecraft account."
        )

    player_uuid = session["uuid"]
    player_name = session["name"]
    token = auth.create_token(player_uuid, player_name)

    return {
        "status": "ok",
        "token": token,
        "uuid": player_uuid,
        "name": player_name
    }


# ------------------ WAYPOINTS ENDPOINTS ------------------

@app.get("/wp/existing")
def get_existing_waypoints():
    try:
        return wp_db.get_all_existing_wp()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database read error: {str(e)}",
        )


@app.get("/wp/my")
def get_my_waypoints(
    uuid: Optional[str] = None,
    authorization: Optional[str] = Header(None)
):
    """
    Fetches all waypoints belonging to the player (pending, approved, declined).
    Automatically restores player state on any new PC or modpack!
    """
    auth_uuid = get_current_user_uuid(authorization)
    target_uuid = auth_uuid or uuid
    if not target_uuid:
        raise HTTPException(status_code=400, detail="UUID or Authorization token is required")

    try:
        return wp_db.get_author_waypoints(target_uuid)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database read error: {str(e)}",
        )


@app.post("/wp/request", status_code=status.HTTP_201_CREATED)
def submit_waypoint_request(
    payload: WaypointPayload,
    authorization: Optional[str] = Header(None)
):
    try:
        wp_data = payload.model_dump(exclude_none=True)
        # Priority: authenticated UUID from verified JWT token
        auth_uuid = get_current_user_uuid(authorization)
        author_uuid = auth_uuid or wp_data.pop("author_uuid", None)
        author_name = wp_data.pop("author_name", None)

        wp_id = wp_db.add_wp_to_requests(wp_data, author_uuid=author_uuid, author_name=author_name)
        return {"status": "ok", "id": wp_id}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database write error: {str(e)}",
        )


@app.post("/wp/request/cancel")
def cancel_waypoint_request(
    payload: AuthorActionRequest,
    authorization: Optional[str] = Header(None)
):
    try:
        auth_uuid = get_current_user_uuid(authorization)
        target_uuid = auth_uuid or payload.author_uuid
        if not target_uuid:
            raise HTTPException(status_code=401, detail="Authentication required")

        success = wp_db.cancel_wp_request(payload.wp_id, author_uuid=target_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Request not found or you are not the author",
            )
        return {"status": "ok", "cancelled": payload.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/delete-by-author")
def delete_waypoint_by_author(
    payload: AuthorActionRequest,
    authorization: Optional[str] = Header(None)
):
    try:
        auth_uuid = get_current_user_uuid(authorization)
        target_uuid = auth_uuid or payload.author_uuid
        if not target_uuid:
            raise HTTPException(status_code=401, detail="Authentication required")

        success = wp_db.delete_by_author(payload.wp_id, author_uuid=target_uuid)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Waypoint not found or you are not the author",
            )
        return {"status": "ok", "deleted": payload.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/status-batch")
def get_status_batch(payload: BatchStatusRequest):
    try:
        return wp_db.get_wp_status_batch(payload.ids)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database read error: {str(e)}",
        )


from fastapi import Depends

@app.get("/wp/requests")
def get_all_requests(_: bool = Depends(verify_moderator)):
    try:
        return wp_db.get_all_wp_requests()
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database read error: {str(e)}",
        )


@app.post("/wp/moderate/approve")
def moderate_approve(req: ApproveRequest, _: bool = Depends(verify_moderator)):
    try:
        success = wp_db.approve_wp_request(
            wp_id=req.wp_id,
            new_parent=req.new_parent,
            edited_wp=req.edited_wp,
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Request with id '{req.wp_id}' not found",
            )
        return {"status": "ok", "approved": req.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/moderate/decline")
def moderate_decline(req: DeclineRequest, _: bool = Depends(verify_moderator)):
    try:
        success = wp_db.decline_wp_request(
            wp_id=req.wp_id,
            reason=req.reason or "Отклонено модератором",
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Request with id '{req.wp_id}' not found",
            )
        return {"status": "ok", "declined": req.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/moderate/block")
def moderate_block(req: BlockRequest, _: bool = Depends(verify_moderator)):
    try:
        success = wp_db.block_wp_request(
            wp_id=req.wp_id,
            reason=req.reason or "Отклонено модератором",
        )
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Request with id '{req.wp_id}' not found",
            )
        return {"status": "ok", "blocked": req.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/admin/save")
def admin_save_waypoint(req: AdminSaveRequest, _: bool = Depends(verify_moderator)):
    try:
        success = wp_db.admin_save_existing_wp(req.waypoint)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid waypoint data (missing id or payload)",
            )
        return {"status": "ok", "saved": req.waypoint.get("id")}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )


@app.post("/wp/admin/delete")
def admin_delete_waypoint(req: AdminDeleteRequest, _: bool = Depends(verify_moderator)):
    try:
        success = wp_db.delete_existing_wp(req.wp_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Waypoint '{req.wp_id}' not found in existing list",
            )
        return {"status": "ok", "deleted": req.wp_id}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Database error: {str(e)}",
        )