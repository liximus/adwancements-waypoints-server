from typing import Any, Dict, List, Optional
import src.db as db


def strip_status_labels(desc: str) -> str:
    if not desc:
        return ""
    desc = desc.replace("\n§e[⏳ На рассмотрении]", "")
    desc = desc.replace("\n§a[✔ Одобрено с изменениями]", "")
    desc = desc.replace("\n§a[✔ Одобрено]", "")
    desc = desc.replace("\n§a[Принято] §e[Изменено]", "")
    desc = desc.replace("\n§a[Принято]", "")
    desc = desc.replace(" §e[Изменено]", "")
    desc = desc.replace("\n§7[Личное]", "")
    idx = desc.find("\n§c[❌ Отклонено:")
    if idx >= 0:
        desc = desc[:idx]
    idx2 = desc.find("\n§c[⛔ Заблокировано:")
    if idx2 >= 0:
        desc = desc[:idx2]
    return desc


def _has_non_parent_changes(orig: dict, edited: dict) -> bool:
    if not orig or not edited:
        return False

    orig_disp = orig.get("display") if isinstance(orig.get("display"), dict) else {}
    edit_disp = edited.get("display") if isinstance(edited.get("display"), dict) else {}

    # Title
    orig_title = orig_disp.get("title")
    edit_title = edit_disp.get("title")
    if orig_title != edit_title:
        return True

    # Description (cleaned of status labels)
    orig_desc = strip_status_labels(orig_disp.get("description") or "")
    edit_desc = strip_status_labels(edit_disp.get("description") or "")
    if orig_desc.strip() != edit_desc.strip():
        return True

    # Icon
    if orig_disp.get("icon") != edit_disp.get("icon"):
        return True

    # Frame
    if orig_disp.get("frame") != edit_disp.get("frame"):
        return True

    # Background
    if orig_disp.get("background") != edit_disp.get("background"):
        return True

    # Criteria / coordinates
    if orig.get("criteria") != edited.get("criteria"):
        return True

    return False


def _clean_uuid(u: Optional[str]) -> str:
    if not u:
        return ""
    return u.lower().replace("-", "")


def add_wp_to_requests(wp: dict, author_uuid: Optional[str] = None, author_name: Optional[str] = None) -> str:
    wp_id = wp.get("id")
    if not wp_id:
        raise ValueError("Missing 'id' in waypoint")

    if author_uuid:
        wp["author_uuid"] = author_uuid
    if author_name:
        wp["author_name"] = author_name

    # Гарантируем, что на сервер сохраняется чистое описание без локальных плашек статуса
    if "display" in wp and isinstance(wp["display"], dict):
        if "description" in wp["display"] and isinstance(wp["display"]["description"], str):
            wp["display"]["description"] = strip_status_labels(wp["display"]["description"])

    db.write("wp:request", wp_id, wp)
    status_entry = {"status": "pending"}
    if author_uuid:
        status_entry["author_uuid"] = author_uuid
        # Добавляем во вторичный индекс запросов игрока
        db.set_add(f"wp:user_requests:{_clean_uuid(author_uuid)}", wp_id)

    db.write("wp:status", wp_id, status_entry)
    return wp_id


def get_wp_status(wp_id: str) -> dict:
    status = db.read("wp:status", wp_id)
    if status:
        return status
    return {"status": "not_found"}


def get_wp_status_batch(wp_ids: List[str]) -> Dict[str, dict]:
    raw_statuses = db.read_batch("wp:status", wp_ids)
    result = {}
    for wp_id in wp_ids:
        st = raw_statuses.get(wp_id)
        if st and isinstance(st, dict):
            result[wp_id] = st
        else:
            result[wp_id] = {"status": "not_found"}
    return result


def cancel_wp_request(wp_id: str, author_uuid: Optional[str] = None) -> bool:
    wp = db.read("wp:request", wp_id)
    if not wp:
        return False
    if author_uuid and wp.get("author_uuid") and _clean_uuid(wp.get("author_uuid")) != _clean_uuid(author_uuid):
        return False

    wp_author = wp.get("author_uuid")
    if wp_author:
        db.set_remove(f"wp:user_requests:{_clean_uuid(wp_author)}", wp_id)

    db.delete("wp:request", wp_id)
    db.delete("wp:status", wp_id)
    return True


def delete_by_author(wp_id: str, author_uuid: str) -> bool:
    # 1. Если еще на рассмотрении
    req = db.read("wp:request", wp_id)
    if req:
        if req.get("author_uuid") and _clean_uuid(req.get("author_uuid")) != _clean_uuid(author_uuid):
            return False
        db.set_remove(f"wp:user_requests:{_clean_uuid(author_uuid)}", wp_id)
        db.delete("wp:request", wp_id)
        db.delete("wp:status", wp_id)
        return True

    # 2. Если уже одобрена и находится в wp:existing
    existing = db.read("wp:existing", wp_id)
    if not existing:
        return False
    if existing.get("author_uuid") and _clean_uuid(existing.get("author_uuid")) != _clean_uuid(author_uuid):
        return False

    db.set_remove(f"wp:user_existing:{_clean_uuid(author_uuid)}", wp_id)
    db.delete("wp:existing", wp_id)
    db.delete("wp:status", wp_id)
    return True


def approve_wp_request(
    wp_id: str,
    new_parent: Optional[str] = None,
    edited_wp: Optional[dict] = None
) -> bool:
    wp = db.read("wp:request", wp_id)
    if not wp:
        return False

    final_wp = edited_wp if edited_wp else wp
    if new_parent:
        final_wp["parent"] = new_parent

    # Сохраняем автора если он был в исходной заявке
    if "author_uuid" in wp and "author_uuid" not in final_wp:
        final_wp["author_uuid"] = wp["author_uuid"]
    if "author_name" in wp and "author_name" not in final_wp:
        final_wp["author_name"] = wp["author_name"]

    if "display" in final_wp and isinstance(final_wp["display"], dict):
        if "description" in final_wp["display"] and isinstance(final_wp["display"]["description"], str):
            final_wp["display"]["description"] = strip_status_labels(final_wp["display"]["description"])

    author_uuid = final_wp.get("author_uuid")
    if author_uuid:
        clean_u = _clean_uuid(author_uuid)
        db.set_remove(f"wp:user_requests:{clean_u}", wp_id)
        db.set_add(f"wp:user_existing:{clean_u}", wp_id)

    # Сравнение изменений без учета parent: "Изменение parent изменением никогда не считается"
    is_edited = False
    if edited_wp:
        is_edited = _has_non_parent_changes(wp, edited_wp)

    db.write("wp:existing", wp_id, final_wp)
    status_entry = {
        "status": "approved_with_changes" if is_edited else "approved",
    }
    if is_edited:
        status_entry["edited"] = True
    if author_uuid:
        status_entry["author_uuid"] = author_uuid
    db.write("wp:status", wp_id, status_entry)
    db.delete("wp:request", wp_id)
    return True


def decline_wp_request(wp_id: str, reason: str = "Отклонено модератором") -> bool:
    wp = db.read("wp:request", wp_id)
    if not wp:
        wp = db.read("wp:existing", wp_id)
    if not wp:
        return False

    author_uuid = wp.get("author_uuid")
    if author_uuid:
        clean_u = _clean_uuid(author_uuid)
        db.set_remove(f"wp:user_requests:{clean_u}", wp_id)
        db.set_remove(f"wp:user_existing:{clean_u}", wp_id)
        db.set_add(f"wp:user_declined:{clean_u}", wp_id)

    db.delete("wp:existing", wp_id)
    status_entry = {"status": "declined", "reason": reason}
    if author_uuid:
        status_entry["author_uuid"] = author_uuid
    db.write("wp:status", wp_id, status_entry)
    db.delete("wp:request", wp_id)
    return True


def block_wp_request(wp_id: str, reason: str = "Отклонено модератором") -> bool:
    wp = db.read("wp:request", wp_id)
    if not wp:
        wp = db.read("wp:existing", wp_id)
    if not wp:
        return False

    author_uuid = wp.get("author_uuid")
    if author_uuid:
        clean_u = _clean_uuid(author_uuid)
        db.set_remove(f"wp:user_requests:{clean_u}", wp_id)
        db.set_remove(f"wp:user_existing:{clean_u}", wp_id)
        db.set_add(f"wp:user_declined:{clean_u}", wp_id)

    db.delete("wp:existing", wp_id)
    status_entry = {"status": "blocked", "reason": reason}
    if author_uuid:
        status_entry["author_uuid"] = author_uuid
    db.write("wp:status", wp_id, status_entry)
    db.delete("wp:request", wp_id)
    return True


def edit_existing_wp(wp_id: str, edited_wp: dict) -> bool:
    existing = db.read("wp:existing", wp_id)
    if not existing:
        return False
    db.write("wp:existing", wp_id, edited_wp)
    return True


def delete_existing_wp(wp_id: str) -> bool:
    existing = db.read("wp:existing", wp_id)
    if not existing:
        return False

    author_uuid = existing.get("author_uuid")
    if author_uuid:
        db.set_remove(f"wp:user_existing:{_clean_uuid(author_uuid)}", wp_id)

    db.delete("wp:existing", wp_id)
    db.delete("wp:status", wp_id)
    return True


def admin_save_existing_wp(wp: dict) -> bool:
    wp_id = wp.get("id")
    if not wp_id:
        return False

    existing = db.read("wp:existing", wp_id)

    # Сохраняем автора если он был
    if existing:
        if "author_uuid" in existing and "author_uuid" not in wp:
            wp["author_uuid"] = existing["author_uuid"]
        if "author_name" in existing and "author_name" not in wp:
            wp["author_name"] = existing["author_name"]

    if "display" in wp and isinstance(wp["display"], dict):
        if "description" in wp["display"] and isinstance(wp["display"]["description"], str):
            wp["display"]["description"] = strip_status_labels(wp["display"]["description"])

    author_uuid = wp.get("author_uuid")
    if author_uuid:
        clean_u = _clean_uuid(author_uuid)
        db.set_add(f"wp:user_existing:{clean_u}", wp_id)

    # Если изменение было принято позже через админ-панель:
    is_edited = False
    if existing:
        is_edited = _has_non_parent_changes(existing, wp)
        old_status = db.read("wp:status", wp_id) or {}
        if old_status.get("edited") or old_status.get("status") == "approved_with_changes":
            is_edited = True

    status_entry = {
        "status": "approved_with_changes" if is_edited else "approved",
    }
    if is_edited:
        status_entry["edited"] = True
    if author_uuid:
        status_entry["author_uuid"] = author_uuid

    db.write("wp:existing", wp_id, wp)
    db.write("wp:status", wp_id, status_entry)
    return True


def get_all_wp_requests() -> List[dict]:
    return db.read_all_from_space("wp:request")


def get_all_existing_wp() -> List[dict]:
    return db.read_all_from_space("wp:existing")


def get_author_waypoints(author_uuid: str) -> Dict[str, Any]:
    """
    Lightning-fast O(1) query using Redis Sets:
    wp:user_requests:<uuid> and wp:user_existing:<uuid>
    No full-table scans!
    """
    clean_u = _clean_uuid(author_uuid)
    if not clean_u:
        return {"requests": [], "existing": [], "statuses": {}}

    # 1. Fetch IDs from Redis Sets
    req_ids = db.set_members(f"wp:user_requests:{clean_u}")
    exist_ids = db.set_members(f"wp:user_existing:{clean_u}")
    declined_ids = db.set_members(f"wp:user_declined:{clean_u}")

    # Fallback / migration: if sets are empty, do scan once to populate
    if not req_ids and not exist_ids:
        for r in get_all_wp_requests():
            if r.get("author_uuid") and _clean_uuid(r.get("author_uuid")) == clean_u and r.get("id"):
                req_ids.append(r["id"])
                db.set_add(f"wp:user_requests:{clean_u}", r["id"])
        for e in get_all_existing_wp():
            if e.get("author_uuid") and _clean_uuid(e.get("author_uuid")) == clean_u and e.get("id"):
                exist_ids.append(e["id"])
                db.set_add(f"wp:user_existing:{clean_u}", e["id"])

    # 2. Batch read with hmget
    my_requests = []
    if req_ids:
        raw_reqs = db.read_batch("wp:request", req_ids)
        my_requests = [v for v in raw_reqs.values() if v]

    my_existing = []
    if exist_ids:
        raw_exist = db.read_batch("wp:existing", exist_ids)
        my_existing = [v for v in raw_exist.values() if v]

    all_ids = list(set(req_ids + exist_ids + declined_ids))
    statuses = get_wp_status_batch(all_ids) if all_ids else {}

    return {
        "requests": my_requests,
        "existing": my_existing,
        "statuses": statuses
    }