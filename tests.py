import src.db as db
import src.wp_db as wp_db
import time

#wp_types: на рассмотрении, отклонена, одобрено, одобрено с правками, одобрена в уже существующий, заблокирована, не найдена

# db.write("wp:existing", "wp_1", '{name=\'asd\', desc=\'desc\'}')
# print(db.read_all_from_space('wp'))
# db.write("wp:requests","wp_1", '{name=\'asdfgd1\', desc=\'descdfg1\'}')
# db.write("wp_type","wp_1", '{name=\'asdfgd2\', desc=\'descdfg2\'}')
# print(db.read_all_from_space('req_wp'))
# print(db.read_all_keys_from_space('req_wp'))

db.clearAll()

wp_db.add_wp_to_requests({'id': 'wp_1', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_2', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_3', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_4', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_5', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_6', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)
wp_db.add_wp_to_requests({'id': 'wp_6', 'icon': 'minecraft:grass_block', 'title': 'title', 'description': 'desc', 'frame': 'task', 'parent': ''})
time.sleep(0.1)




# print(wp_db.get_all_wp_requests())
# print(wp_db.get_all_existing_wp())
# print(db.read_all_from_space('wp_status'))
# wp_db.approve_wp_request("wp_2")
# print()
# print(wp_db.get_all_wp_requests())
# print(wp_db.get_all_existing_wp())
# print(db.read_all_from_space('wp_status'))