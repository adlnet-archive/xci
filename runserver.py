from xci import config_app
from pymongo import MongoClient

# Init db
# mongo = MongoClient()
# db = mongo.xci

# Check if badgeclasses are empty
# if not 'badgeclass' in db.collection_names() and db.badgeclass.count() == 0:
	# Get domain for the issuer
# 	domain = raw_input("Please enter the domain (no ending slash):")

# 	# Seed data needed for badges
# 	seed_data = [
# 	{
# 		"name": "Tetris Times - 3 Minutes",
# 		"description": "Played for at least 3 minutes in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Times - 6 Minutes",
# 		"description": "Played for at least 6 minutes in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Times - 9 Minutes",
# 		"description": "Played for at least 9 minutes in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Times - 12 Minutes",
# 		"description": "Played for at least 12 minutes in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Times - 15 Minutes",
# 		"description": "Played for at least 15 minutes in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},				
# 	{
# 		"name": "Tetris Levels - Level 5",
# 		"description": "Passed 5 levels in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Levels - Level 10",
# 		"description": "Passed 10 levels in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Levels - Level 15",
# 		"description": "Passed 15 levels in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Levels - Level 20",
# 		"description": "Passed 20 levels in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Lines - 20 Lines",
# 		"description": "Made 20 lines in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Lines - 40 Lines",
# 		"description": "Made 40 lines in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Lines - 60 Lines",
# 		"description": "Made 60 lines in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Lines - 80 Lines",
# 		"description": "Made 80 lines in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Lines - 100 Lines",
# 		"description": "Made 100 lines in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 50,000 Points",
# 		"description": "Achieved 50,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 100,000 Points",
# 		"description": "Achieved 100,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 200,000 Points",
# 		"description": "Achieved 200,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 400,000 Points",
# 		"description": "Achieved 400,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 800,000 Points",
# 		"description": "Achieved 800,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 1,000,000 Points",
# 		"description": "Achieved 1,000,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 1,500,000 Points",
# 		"description": "Achieved 1,500,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	},
# 	{
# 		"name": "Tetris Scores - 2,000,000 Points",
# 		"description": "Achieved 2,000,000 points in tetris.",
# 		"image": domain + "/tetris/classes/image",
# 		"criteria": "http://12.109.40.34/performance-framework/xapi/tetris.xml",
# 		"issuer": domain + "/tetris/issuer"
# 	}
# ]
# import datetime
# import pytz

#             for perf in perfs:
#                 badgeassertion = {
#                                 'recipient':{
#                                     'type': 'email',
#                                     'hashed': False,
#                                     'identity': self.userobj['email']
#                                     },
#                                 'issuedOn': datetime.datetime.now(pytz.utc).isoformat(),
#                                 'badge':'',
#                                 'verify':{
#                                     'type': 'hosted',
#                                     'url': 'URL OF LRS/STATEMENTS GOES HERE'
#                                     }
#                             }


	
# 	# Insert docs to get UID
# 	for doc in seed_data:
# 		import pdb
# 		pdb.set_trace()
# 		_id = db.badgeclass.insert(doc)
# 		image_parts = doc['image'].rsplit('/', 1)
# 		# doc['image'] = doc['image'] + str(_id)
# 		doc['image'] = image_parts[0] + '/' + str(_id) + '/' + image_parts[1]
# 		db.badgeclass.update({"_id":_id}, doc)

	# # Update docs' image path with UID
	# badgeclasses = db.badgeclass.find()
	# for b in badgeclasses:
	# 	image = b['image'].rsplit('/', 1)
	# 	b['image'] = image[0] + '/' + str(b['_id']) + '/' + image[1]
	# 	db.badgeclass.update({"_id":b['_id']}, b)

# mongo.close()

# Run the app
app = config_app()
app.run(debug=True)