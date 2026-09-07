from typing import Optional
import src.db as db

DEFAULT_SERVER = "pepeland"


def _space(server: str, category: str) -> str:
    return f"wp:{server}:{category}"


def add_wp_to_requests(wp: dict, server: str = DEFAULT_SERVER) -> str:
    wp_id = wp.get("id")
    if not wp_id:
        raise ValueError("Вейпоинт должен содержать поле 'id'")

    db.write(_space(server, "request"), wp_id, wp)
    db.write(_space(server, "status"), wp_id, {"type": "pending"})
    return wp_id


def approve_wp_request(wp_id: str, server: str = DEFAULT_SERVER) -> bool:
    wp = db.read(_space(server, "request"), wp_id)
    if wp:
        db.write(_space(server, "existing"), wp_id, wp)
        db.write(_space(server, "status"), wp_id, {"type": "approved"})
        db.delete(_space(server, "request"), wp_id)
        return True
    return False


def approve_wp_request_with_edit(wp_id: str, edited_wp: dict, server: str = DEFAULT_SERVER) -> bool:
    wp = db.read(_space(server, "request"), wp_id)
    if wp:
        db.write(_space(server, "existing"), wp_id, edited_wp)
        db.write(_space(server, "status"), wp_id, {"type": "approved_with_edit"})
        db.delete(_space(server, "request"), wp_id)
        return True
    return False


def decline_wp_request(wp_id: str, reason: Optional[str] = None, server: str = DEFAULT_SERVER) -> bool:
    wp = db.read(_space(server, "request"), wp_id)
    if wp:
        status_data = {"type": "declined"}
        if reason:
            status_data["reason"] = reason
        db.write(_space(server, "status"), wp_id, status_data)
        db.delete(_space(server, "request"), wp_id)
        return True
    return False


def block_wp_request(wp_id: str, reason: Optional[str] = None, server: str = DEFAULT_SERVER) -> bool:
    wp = db.read(_space(server, "request"), wp_id)
    if wp:
        status_data = {"type": "blocked"}
        if reason:
            status_data["reason"] = reason
        db.write(_space(server, "status"), wp_id, status_data)
        db.delete(_space(server, "request"), wp_id)
        return True
    return False


def get_wp_status(wp_id: str, server: str = DEFAULT_SERVER) -> dict:
    status = db.read(_space(server, "status"), wp_id)
    if status:
        return status
    return {"type": "not_found"}


def get_wp_request(wp_id: str, server: str = DEFAULT_SERVER) -> Optional[dict]:
    return db.read(_space(server, "request"), wp_id)


def get_all_wp_requests(server: str = DEFAULT_SERVER) -> list[dict]:
    return db.read_all_from_space(_space(server, "request"))


def get_all_existing_wp(server: str = DEFAULT_SERVER) -> list[dict]:
    return db.read_all_from_space(_space(server, "existing"))


def edit_existing_wp(wp_id: str, edited_wp: dict, server: str = DEFAULT_SERVER) -> bool:
    existing = db.read(_space(server, "existing"), wp_id)
    if existing:
        db.write(_space(server, "existing"), wp_id, edited_wp)
        return True
    return False


def delete_existing_wp(wp_id: str, server: str = DEFAULT_SERVER) -> bool:
    return db.delete(_space(server, "existing"), wp_id)