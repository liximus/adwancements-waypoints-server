import os
from typing import Optional, Union
from fastapi import FastAPI, HTTPException, Security, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader

from src.models import WaypointModel, WaypointRequestPayload, DeclinePayload
import src.wp_db as wp_db

app = FastAPI(
    title="Advancement Waypoints Server",
    description="API для синхронизации и модерации вейпоинтов/ачивок в Minecraft",
    version="1.0.0"
)

# CORS для возможности подключения веб-панелей
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

admin_header = APIKeyHeader(name="X-Admin-Password", auto_error=False)


def verify_admin(password: Optional[str] = Security(admin_header)):
    expected_password = os.getenv("ADMIN_PASSWORD", "admin")
    if not password or password != expected_password:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Неверный пароль администратора (Invalid admin password)",
        )
    return True


def get_wp_data(payload: Union[WaypointRequestPayload, WaypointModel]) -> dict:
    if isinstance(payload, WaypointRequestPayload):
        return payload.data.model_dump() if hasattr(payload.data, "model_dump") else payload.data.dict()
    return payload.model_dump() if hasattr(payload, "model_dump") else payload.dict()


# -------------------------------------------------------------
# Базовый health check
# -------------------------------------------------------------
@app.get("/")
def health_check():
    return {
        "status": "ok",
        "default_server": wp_db.DEFAULT_SERVER,
        "message": "Advancement Waypoints API is running"
    }


# -------------------------------------------------------------
# Публичные эндпоинты (для мода и игроков)
# -------------------------------------------------------------
@app.post("/wp/request", status_code=status.HTTP_201_CREATED, tags=["Public"])
@app.post("/{server}/wp/request", status_code=status.HTTP_201_CREATED, tags=["Public"])
def create_request(
    payload: Union[WaypointRequestPayload, WaypointModel],
    server: str = wp_db.DEFAULT_SERVER,
):
    try:
        wp_data = get_wp_data(payload)
        wp_id = wp_db.add_wp_to_requests(wp_data, server=server)
        return {"status": "ok", "id": wp_id, "server": server}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database write error: {str(e)}"
        )


@app.get("/wp/existing", tags=["Public"])
@app.get("/{server}/wp/existing", tags=["Public"])
def get_existing(server: str = wp_db.DEFAULT_SERVER):
    try:
        return wp_db.get_all_existing_wp(server=server)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database read error: {str(e)}"
        )


@app.get("/wp/status/{wp_id}", tags=["Public"])
@app.get("/{server}/wp/status/{wp_id}", tags=["Public"])
def check_status(wp_id: str, server: str = wp_db.DEFAULT_SERVER):
    try:
        wp_status = wp_db.get_wp_status(wp_id, server=server)
        return {"id": wp_id, "status": wp_status, "server": server}
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database read error: {str(e)}"
        )


# -------------------------------------------------------------
# Админские эндпоинты (требуется пароль в заголовке X-Admin-Password)
# -------------------------------------------------------------
@app.get("/wp/requests", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.get("/{server}/wp/requests", dependencies=[Depends(verify_admin)], tags=["Admin"])
def get_requests(server: str = wp_db.DEFAULT_SERVER):
    try:
        return wp_db.get_all_wp_requests(server=server)
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Database read error: {str(e)}"
        )


@app.post("/wp/approve/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.post("/{server}/wp/approve/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def approve_request(wp_id: str, server: str = wp_db.DEFAULT_SERVER):
    success = wp_db.approve_wp_request(wp_id, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Заявка '{wp_id}' не найдена")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' успешно одобрен"}


@app.post("/wp/approve-edit/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.post("/{server}/wp/approve-edit/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def approve_request_with_edit(
    wp_id: str,
    payload: Union[WaypointRequestPayload, WaypointModel],
    server: str = wp_db.DEFAULT_SERVER,
):
    wp_data = get_wp_data(payload)
    success = wp_db.approve_wp_request_with_edit(wp_id, wp_data, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Заявка '{wp_id}' не найдена")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' одобрен с правками"}


@app.post("/wp/decline/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.post("/{server}/wp/decline/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def decline_request(
    wp_id: str,
    payload: Optional[DeclinePayload] = None,
    server: str = wp_db.DEFAULT_SERVER,
):
    reason = payload.reason if payload else None
    success = wp_db.decline_wp_request(wp_id, reason=reason, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Заявка '{wp_id}' не найдена")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' отклонен"}


@app.post("/wp/block/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.post("/{server}/wp/block/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def block_request(
    wp_id: str,
    payload: Optional[DeclinePayload] = None,
    server: str = wp_db.DEFAULT_SERVER,
):
    reason = payload.reason if payload else None
    success = wp_db.block_wp_request(wp_id, reason=reason, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Заявка '{wp_id}' не найдена")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' заблокирован"}


@app.put("/wp/existing/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.put("/{server}/wp/existing/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def edit_existing(
    wp_id: str,
    payload: Union[WaypointRequestPayload, WaypointModel],
    server: str = wp_db.DEFAULT_SERVER,
):
    wp_data = get_wp_data(payload)
    success = wp_db.edit_existing_wp(wp_id, wp_data, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Существующий вейпоинт '{wp_id}' не найден")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' обновлен"}


@app.delete("/wp/existing/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
@app.delete("/{server}/wp/existing/{wp_id}", dependencies=[Depends(verify_admin)], tags=["Admin"])
def delete_existing(wp_id: str, server: str = wp_db.DEFAULT_SERVER):
    success = wp_db.delete_existing_wp(wp_id, server=server)
    if not success:
        raise HTTPException(status_code=404, detail=f"Существующий вейпоинт '{wp_id}' не найден")
    return {"status": "ok", "message": f"Вейпоинт '{wp_id}' удален"}