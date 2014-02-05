from flask_wtf import Form
from wtforms import TextField, PasswordField
from wtforms.validators import DataRequired

class LoginForm(Form):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])

class RegistrationForm(Form):
	username = TextField('Username', validators=[DataRequired()])
	password = PasswordField('Password', validators=[DataRequired()])
	first_name = TextField('First Name', validators=[DataRequired()])
	last_name = TextField('Last Name', validators=[DataRequired()])
	email = TextField('Email', validators=[DataRequired()])

class FrameworksForm(Form):
	framework_uri = TextField('Framework URI', validators=[DataRequired()])