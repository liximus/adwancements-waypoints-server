import src.db as db
import src.wp_db as wp_db

print("=== Тестирование логики вейпоинтов ===")

server = "pepeland"
test_id = "test_wp_diamond"

test_wp = {
    "id": test_id,
    "title": "Алмазная жила",
    "description": "Точка на высоте Y=-58",
    "icon": "minecraft:diamond_ore",
    "frame": "task",
    "parent": "",
    "x": 120.5,
    "y": -58.0,
    "z": 450.0,
    "author": "Steve"
}

# 1. Добавляем заявку
print(f"1. Добавление заявки {test_id}...")
wp_db.add_wp_to_requests(test_wp, server=server)

# 2. Проверяем статус заявки
status = wp_db.get_wp_status(test_id, server=server)
print("2. Статус заявки:", status)
assert status.get("type") == "pending", f"Ожидался статус 'pending', получено: {status}"

# 3. Смотрим все заявки
requests = wp_db.get_all_wp_requests(server=server)
print(f"3. Найдено заявок: {len(requests)}")
assert any(r.get("id") == test_id for r in requests), "Заявка не найдена в списке заявок!"

# 4. Одобряем заявку
print("4. Одобрение заявки...")
approved = wp_db.approve_wp_request(test_id, server=server)
assert approved is True, "Не удалось одобрить заявку"

# 5. Проверяем новый статус
new_status = wp_db.get_wp_status(test_id, server=server)
print("5. Новый статус:", new_status)
assert new_status.get("type") == "approved", f"Ожидался статус 'approved', получено: {new_status}"

# 6. Проверяем в существующих
existing = wp_db.get_all_existing_wp(server=server)
print(f"6. Найдено подтвержденных вейпоинтов: {len(existing)}")
assert any(w.get("id") == test_id for w in existing), "Вейпоинт не найден в списке существующих!"

# 7. Очищаем тестовый вейпоинт
wp_db.delete_existing_wp(test_id, server=server)
db.delete(f"wp:{server}:status", test_id)
print("7. Тестовый вейпоинт удален из базы.")

print("\n Все тесты успешно пройдены!")