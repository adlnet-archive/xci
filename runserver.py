from xci import config_app
from pymongo import MongoClient

# Init db
mongo = MongoClient()
db = mongo.xci

# Check if badgeclasses are empty
if not 'badgeclass' in db.collection_names() and db.badgeclass.count() == 0:
	# Get domain for the issuer
	domain = raw_input("Please enter the domain (no ending slash):")

	# Seed data needed for badges
	seed_data = [
	{
		"name": "Tetris Times",
		"description": "Played for a long time in tetris.",
		"image": domain + "/tetris/times_badge",
		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
		"issuer": domain + "/tetris/issuer"
	},
	{
		"name": "Tetris Levels",
		"description": "Passed an impressive amount of levels in tetris.",
		"image": domain + "/tetris/levels_badge",
		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
		"issuer": domain + "/tetris/issuer"
	},
	{
		"name": "Tetris Lines",
		"description": "Made a bunch of lines in tetris.",
		"image": domain + "/tetris/lines_badge",
		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
		"issuer": domain + "/tetris/issuer"
	},
	{
		"name": "Tetris Scores",
		"description": "Achieved a worthy score in tetris.",
		"image": domain + "/tetris/scores_badge",
		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
		"issuer": domain + "/tetris/issuer"
	}
]
	
	# Insert docs to get UID
	for doc in seed_data:
		db.badgeclass.insert(doc)
	
	# Update docs' image path with UID
	badgeclasses = db.badgeclass.find()
	for b in badgeclasses:
		image = b['image'].rsplit('/', 1)
		b['image'] = image[0] + '/' + str(b['_id']) + '/' + image[1]
		db.badgeclass.update({"_id":b['_id']}, b)

mongo.close()

# Run the app
app = config_app()
app.run(debug=True)