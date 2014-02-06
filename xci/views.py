from xci import app, competency
from flask import render_template, redirect, flash, url_for, request, make_response
from forms import LoginForm, RegistrationForm, FrameworksForm
from models import User
from flask_login import LoginManager, login_user, login_required, logout_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import json

login_manager = LoginManager()
login_manager.init_app(app)

mongo = MongoClient()
db = mongo.xci

def add_login_to_return_dict(r_dict):
	r_dict['login_form'] = LoginForm()
	return r_dict

@login_manager.user_loader
def load_user(user):
	if isinstance(user, basestring):
		userobj = User(user, 'get')
		u_id = userobj.get_id()
		return userobj
	else:
		u_id = user.get_id()
		return user

@app.route('/', methods=['GET'])
def index():
    return_dict = add_login_to_return_dict({})
    return render_template('home.html', **return_dict)
    # uri = request.args.get('uri', None)
    # if uri:
    #     p = competency.parseMedBiq(uri)
    #     try:
    #         resp = make_response(json.dumps(p), 200)
    #         resp.headers['Content-Type'] = "application/json"
    #         return resp
    #     except Exception as e:
    #         return make_response("%s<br>%s" % (str(e), p), 200)
    #         # return make_response("fail <br> %s" % repr(p), 200)

    # return '''yay we dids it! 
    #           <br>DEBUG: %s 
    #           <br>SECRET: %s
    #           <br><a href="./?uri=http://adlnet.gov/competency-framework/scorm/choosing-an-lms.xml">choose lms</a>
    #           <br><a href="./?uri=http://adlnet.gov/competency-framework/computer-science/basic-programming.xml">programming</a>
    #           <br><a href="./?uri=http://12.109.40.34/performance-framework/xapi/tetris.xml">perf tetris</a>''' % (app.config['DEBUG'], app.config['SECRET_KEY'])


@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route('/login', methods=["POST"])
def login():
	lf = LoginForm(request.form)
	next = request.args.get("next")

	if lf.validate_on_submit():
		user = User(lf.username.data, generate_password_hash(lf.password.data))
		login_user(user)
		return redirect(next or url_for("index"))
	else:
		import pdb
		pdb.set_trace()
		if next == '/':
			return render_template('home.html',login_form=lf)
		elif next == '/frameworks':
			return render_template('frameworks.html', login_form=lf, frameworks_form=FrameworksForm(), cfwks=competency.get_all_comp_frameworks())
		elif next == '/sign_up':
			return render_template('sign_up', login_form=lf, signup_form=RegistrationForm())
		elif next == '/me':
			return render_template('me', login_form=lf)

@app.route('/sign_up', methods=["GET", "POST"])
def sign_up():
	if request.method == 'GET':
		return_dict = {'signup_form': RegistrationForm(), 'hide': True}
		return render_template('sign_up.html', **add_login_to_return_dict(return_dict))
	else:
		rf = RegistrationForm(request.form)
		if rf.validate_on_submit():
			users = db.userprofiles
			users.insert({'username': rf.username.data, 'password':generate_password_hash(rf.password.data), 'email':rf.email.data,
				'first_name':rf.first_name.data, 'last_name':rf.last_name.data, 'competencies':[], 'compfwks':[], 'lrsprofiles':[]})
			
			user = User(rf.username.data, generate_password_hash(rf.password.data))
			login_user(user)
			return redirect(request.args.get('next') or url_for('index'))
		return render_template(url_for('sign_up'), rf)


@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
	return_dict = {'frameworks_form': FrameworksForm()}
	if request.method == 'GET':
		return_dict['cfwks'] = competency.get_all_comp_frameworks()
	else:
		ff = FrameworksForm(request.form)
		#validate form here somehow
		try:
			#add to system
			pass
		except Exception, e:
			raise e
	return render_template('frameworks.html', **add_login_to_return_dict(return_dict))


@app.route('/me', methods=["GET"])
@login_required
def me():
	return render_template('me.html')

