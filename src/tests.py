import db
import wp_db

#wp_types: на рассмотрении, отклонена, одобрено, одобрено с правками, одобрена в уже существующий, заблокирована, не найдена

# db.write("wp:existing", "wp_1", '{name=\'asd\', desc=\'desc\'}')
# print(db.read_all_from_space('wp'))
# db.write("wp:requests","wp_1", '{name=\'asdfgd1\', desc=\'descdfg1\'}')
# db.write("wp_type","wp_1", '{name=\'asdfgd2\', desc=\'descdfg2\'}')
# print(db.read_all_from_space('req_wp'))
# print(db.read_all_keys_from_space('req_wp'))

db.clearAll()

wp_db.add_wp_to_requests({'id': 'wp_2', 'name': 'namee', 'desc': 'desc'})
print(wp_db.get_all_wp_requests())
print(wp_db.get_all_existing_wp())
print(db.read_all_from_space('wp_status'))
wp_db.approve_wp_request("wp_2")
print()
print(wp_db.get_all_wp_requests())
print(wp_db.get_all_existing_wp())
print(db.read_all_from_space('wp_status'))