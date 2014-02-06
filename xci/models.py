from flask_login import UserMixin
from pymongo import MongoClient

mongo = MongoClient()
db = mongo.xci

class User(UserMixin):
	def __init__(self, userid, password):
		self.id = userid
		self.password = password

	def get_id(self):
		try:
			user = db.userprofiles.find_one({"username":self.id})
			return unicode(self.id)
		except Exception, e:
			raise e