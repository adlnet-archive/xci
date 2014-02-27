from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, RadioField, HiddenField
from wtforms.validators import DataRequired
from pymongo import MongoClient
from werkzeug.security import check_password_hash
from rfc3987 import parse

mongo = MongoClient()
db = mongo.xci

class LoginForm(Form):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		self.user = None

	def validate(self):
		rv = Form.validate(self)
		if not rv:
			return False

		user = db.userprofiles.find_one({'username':self.username.data})
		if user is None:
			self.username.errors.append('Unknown username')
			return False

		if not check_password_hash(user['password'],self.password.data):
			self.password.errors.append('Invalid password')
			return False

		self.user = user
		return True

class RegistrationForm(Form):
	first_name = TextField('First Name', validators=[DataRequired()])
	last_name = TextField('Last Name', validators=[DataRequired()])
	email = TextField('Email', validators=[DataRequired()])
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	role = RadioField('Role', validators=[DataRequired()], choices=[('admin', 'admin'), ('teacher', 'teacher'), ('student','student')])

	def __init__(self, *args, **kwargs):
		Form.__init__(self, *args, **kwargs)
		self.user = None

	def validate(self):
		rv = Form.validate(self)
		if not rv:
			return False

		user = db.userprofiles.find_one({'username':self.username.data})
		if user:
			self.username.errors.append('Username already exists')
			return False

		self.user = user
		return True	

class FrameworksForm(Form):
	framework_uri = TextField('Framework URI', validators=[DataRequired()])

class SettingsForm(Form):
	name = TextField('Name', validators=[DataRequired()])
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	default = BooleanField('Default')

class SearchForm(Form):
	search = TextField('Search', validators=[DataRequired()])

class CompetencyEditForm(Form):
	title = TextField('Title', validators=[DataRequired()])
	description = TextField('Description', validators=[DataRequired()])
	uri = TextField('URI', validators=[DataRequired(), validateURI])
	ids = TextField('Other Ids')
	ctype = TextField('Competency Type')
	levels = TextField('Levels')
	relations = TextField('Parent/siblings')
	objectids = TextField('Related Objects')	

def validateURI(form, field):
	try: 
		parse(field.data, rule='IRI')
		return True
	except:
		return False