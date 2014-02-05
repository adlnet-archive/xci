from xci import app, competency
from flask import render_template, redirect, flash, url_for, request, make_response
from forms import LoginForm, RegistrationForm, FrameworksForm
from flask_login import LoginManager, login_user
import json

login_manager = LoginManager()
login_manager.init_app(app)

def add_login_to_return_dict(r_dict):
	r_dict['login_form'] = LoginForm()
	return r_dict

@login_manager.user_loader
def load_user(userid):
	# return User.get(userid)
	# this is where we would grab the user from the db
	return true

@app.route('/', methods=['GET'])
def index():
    # return 'yay we dids it! <br>DEBIG: %s <br>SECRET: %s' % (app.config['DEBUG'], app.config['SECRET_KEY'])
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



@app.route('/login', methods=["POST"])
def login():
	form = LoginForm()
	if form.validate_on_submit():
		# login_user(user)
		return redirect(request.args.get("next") or url_for("index"))

@app.route('/sign_up', methods=["GET", "POST"])
def sign_up():

	if request.method == 'GET':
		return_dict = {'signup_form': SystemUserForm(), 'hide': True}
		return render_template('sign_up.html', **add_login_to_return_dict(return_dict))
	else:
		rf = RegistrationForm()
		#validate form somehow
		#save user to db
		#log user in
		return redirect(url_for('index'))


@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
	return_dict = {'frameworks_form': FrameworksForm()}
	if request.method == 'GET':
		return_dict['cfwks'] = competency.get_all_comp_frameworks()
	else:
		ff = FrameworksForm(request.POST)
		#validate form here somehow
		try:
			#add to system
			pass
		except Exception, e:
			raise e
	return render_template('frameworks.html', **add_login_to_return_dict(return_dict))


@app.route('/me', methods=["GET"])
def me():
	return render_template('me.html')

