import json
from flask_wtf import Form
from wtforms import TextField, PasswordField, BooleanField, RadioField, HiddenField
from wtforms.validators import DataRequired
from pymongo import MongoClient
from werkzeug.security import check_password_hash
from rfc3987 import parse

# Set db
mongo = MongoClient()
db = mongo.xci

# Validate the uri field in the form
def validateURI(form, field):
    parse(field.data, rule='IRI')

class LoginForm(Form):
    username = TextField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        self.user = None

    # Make sure the username exists in db and the password is correct for the user to login
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

    # Check if the username or email already exist in the db
    def validate(self):
        rv = Form.validate(self)
        if not rv:
            return False

        user = db.userprofiles.find_one({'username':self.username.data})
        if user:
            self.username.errors.append('Username already exists')
            return False

        user = db.userprofiles.find_one({'email':self.email.data})
        if user:
            self.email.errors.append('Email already exists')
            return False

        self.user = user
        return True 

class FrameworksForm(Form):
    framework_uri = TextField('Framework URI', validators=[DataRequired()])

class SettingsForm(Form):
    name = TextField('Name', validators=[DataRequired()])
    username = TextField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    default = BooleanField('Default', default=False)

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
    linked_content = TextField('Linked Content')  

    def __init__(self, *args, **kwargs):
        Form.__init__(self, *args, **kwargs)
        obj = kwargs.get('obj', False)
        if obj:
            self.title.data = obj.get('title', None)
            self.description.data = obj.get('description', None)
            self.uri.data = obj.get('uri', None)
            # only json dump if there's a value... cuz json'll make it null
            # and then cause it to be saved later as 'ids':'null'
            self.ids.data = json.dumps(obj.get('ids', None)) if obj.get('ids', None) else obj.get('ids', None)
            self.ctype.data = obj.get('type', None)
            self.levels.data = json.dumps(obj.get('levels', None)) if obj.get('levels', None) else obj.get('levels', None)
            self.relations.data = json.dumps(obj.get('relations', None)) if obj.get('relations', None) else obj.get('relations', None)
            self.linked_content.data = json.dumps(obj.get('linked_content', None)) if obj.get('linked_content', None) else obj.get('linked_content', None)

    # Make sure all fields are in proper format
    def toDict(self):
        d = {'title':self.title.data,
             'description':self.description.data,
             'uri':self.uri.data,
            }
        if self.ids.data:
            d['ids'] = json.loads(self.ids.data)
        if self.ctype.data:
            d['type'] = self.ctype.data
        if self.levels.data:
            d['levels'] = json.loads(self.levels.data)
        if self.relations.data:
            d['relations'] = json.loads(self.relations.data)
        if self.linked_content.data:
            d['linked_content'] = json.loads(self.linked_content.data)

        return d

    def toJSON(self):
        return json.dumps(self.toDict())


