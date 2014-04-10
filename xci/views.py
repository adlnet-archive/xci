import base64
import json
import models
import requests
from xci import app, competency, performance
from xci.competency import MBCompetency as mbc
from functools import wraps
from flask import render_template, redirect, flash, url_for, request, make_response, Response, jsonify, abort
from forms import LoginForm, RegistrationForm, FrameworksForm, SettingsForm, SearchForm, CompetencyEditForm
from models import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash

# Init login_manager
login_manager = LoginManager()
login_manager.init_app(app)

# Init db
mongo = MongoClient()
db = mongo.xci

# lr uri to obtain docs
LR_NODE = "http://node01.public.learningregistry.net/obtain?request_ID="

# Checks if the user has admin privileges
def check_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        person = current_user
        if not 'admin' in person.roles:
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

# Load the user (needed for login manager)
@login_manager.user_loader
def load_user(user):
    if isinstance(user, basestring):
        userobj = User(user, 'get')
        u_id = userobj.get_id()
        return userobj
    else:
        u_id = user.get_id()
        return user

# Return home template
@app.route('/', methods=['GET'])
def index():
    uri = request.args.get('uri', None)
    # the links on the competency page route back to this
    # the uri param says which comp to load
    if uri:
        p = competency.parseComp(uri)
        try:
            return redirect(url_for("competencies"))
        except Exception as e:
            return make_response("%s<br>%s" % (str(e), p), 200)

    badges = [x for x in db.badgeclass.find()]
    for b in badges:
        b['_id'] = str(b['_id'])

    return render_template('home.html', badges=badges)
    
# Logout user
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

# Login user
@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html', login_form=LoginForm())
    else:
        # If posting and validated, log them in
        lf = LoginForm(request.form)
        if lf.validate_on_submit():
            user = User(lf.username.data, generate_password_hash(lf.password.data))
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", login_form=lf)

# Register user
@app.route('/sign_up', methods=["GET", "POST"])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html', signup_form=RegistrationForm(), hide=True)
    else:
        # Add necessary roles as needed
        rf = RegistrationForm(request.form)
        if rf.validate_on_submit():
            role = rf.role.data
            if role == 'admin':
                role = ['admin', 'teacher', 'student']
            elif role == 'teacher':
                role = ['teacher', 'student']
            else:
                role = ['student']

            # Add user to db and login
            users = db.userprofiles
            users.insert({'username': rf.username.data, 'password':generate_password_hash(rf.password.data), 'email':rf.email.data,
                'first_name':rf.first_name.data, 'last_name':rf.last_name.data, 'competencies':{}, 'compfwks':{}, 'perfwks':{}, 'lrsprofiles':[], 'roles':role})

            user = User(rf.username.data, generate_password_hash(rf.password.data))
            login_user(user)
            return redirect(url_for('index'))
        return render_template('sign_up.html', signup_form=rf, hide=True)

# Competency view
@app.route('/competencies')
def competencies():
    # Look for comp args, if none display all comps
    d = {}
    uri = request.args.get('uri', None)
    uview = request.args.get('userview', False)
    mb = request.args.get('mb', False)
    if uri:      
        d['uri'] = uri
        comp = models.getCompetency(uri, objectid=True)
        d['cid'] = comp.pop('_id')
        d['comp'] = comp
        d['userview'] = uview
        # If medbiq comp display xml if so since it's the original and not lossy internal one
        if mb:
            if not comp.get('edited', False) and competency.isMB(comp):
                try:
                    thexml = requests.get(competency.addXMLSuffix(comp['uri'])).text
                except:
                    thexml = mbc.toXML(comp)
            else:
                thexml = mbc.toXML(comp)
            return Response(thexml, mimetype='application/xml')
        else:
            compuri = d['uri']
            if 'adlnet' in d['uri']:
                compuri = compuri[:7] + 'www.' + compuri[7:]
            url = "https://node01.public.learningregistry.net/slice?any_tags=%s" % compuri
            resp = requests.get(url)
            ids = []
            if resp.status_code == 200:
                lrresults = json.loads(resp.content)
                ids = [s['doc_ID'] for s in lrresults['documents']]
                for d_id in ids:
                    models.updateCompetencyLR(d['cid'], LR_NODE + d_id + '&by_doc_ID=T')
                updated_comp = models.getCompetency(uri, objectid=True)
                d['comp'] = updated_comp

            return render_template('comp-details.html', **d)

    d['comps'] = models.findCompetencies()
    return render_template('competencies.html', **d)

# Return competency frameworks
@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
    if request.method == 'GET':
        # Determine if requesting specific fwk or not
        uri = request.args.get('uri', None)
        uview = request.args.get('userview', False)
        if uri:
            d = {}
            d['uri'] = uri
            d['fwk'] = models.getCompetencyFramework(uri)
            d['userview'] = uview
            return render_template('compfwk-details.html', **d)

        return_dict = {'frameworks_form': FrameworksForm()}
    else:
        # Validate submitted fwk uri/parse/add to system
        ff = FrameworksForm(request.form)
        if ff.validate_on_submit():
            #add to system
            competency.parseComp(ff.framework_uri.data)
            return_dict = {'frameworks_form': FrameworksForm()}
        else:
            return_dict = {'frameworks_form': ff}

    return_dict['cfwks'] = models.findCompetencyFrameworks()
    return render_template('frameworks.html', **return_dict)

# Return performance frameworks
@app.route('/perfwks', methods=["GET", "POST"])
def perfwks():
    d = {}
    if request.method == 'GET':
        # Determine if asking for specific fwk or not
        uri = request.args.get('uri', None)
        uview = request.args.get('userview', False)
        if uri:
            d = {}
            d['uri'] = uri
            d['fwk'] = models.getPerformanceFramework(uri)
            d['userview'] = uview
            return render_template('perfwk-details.html', **d)
        d['frameworks_form'] = FrameworksForm()
    else:
        # Validate submitted fwk uri/parse/add to system
        ff = FrameworksForm(request.form)
        if ff.validate_on_submit():
            #add to system
            competency.parseComp(ff.framework_uri.data)
            d['frameworks_form'] = FrameworksForm()
        else:
            d['frameworks_form'] = ff

    d['pfwks'] = models.findPerformanceFrameworks()
    return render_template('performancefwks.html', **d)

# Return all data pertaining to user
@app.route('/me', methods=["GET"])
@login_required
def me():
    username = current_user.id
    user = models.getUserProfile(username)
    user_comps = user['competencies'].values()
    user_fwks = user['compfwks'].values()
    user_pfwks = user['perfwks'].values()

    # Calculate complete competencies for users and return count
    completed_comps = sum(1 for c in user_comps if c.get('completed',False))
    started_comps = len(user_comps) - completed_comps   
    name = user['first_name'] + ' ' + user['last_name']

    return render_template('me.html', comps=user_comps, fwks=user_fwks, pfwks=user_pfwks, completed=completed_comps, started=started_comps, name=name, email=user['email'])

# Add comps/fwks/perfwks to the user
@app.route('/me/add', methods=["POST"])
@login_required
def add_comp():
    # Hashes of the uri of the comp are used to store them in the userprofile object
    if request.form.get('comp_uri', None):
        models.addCompToUserProfile(request.form.get('comp_uri', None), current_user.id)
    elif request.form.get('fwk_uri', False):
        models.addFwkToUserProfile(request.form.get('fwk_uri', None), current_user.id)
    elif request.form.get('perfwk_uri', False):
        models.addPerFwkToUserProfile(request.form.get('perfwk_uri', None), current_user.id)

    return redirect(url_for("me"))

# Loads common core xml from xml document outside of project
@app.route('/cc')
def load_cc():
    from xci import commoncore
    commoncore.getCommonCore()
    return redirect(url_for("competencies"))

# Return userprofile for settings page
@app.route('/me/settings', methods=["GET"])
@login_required
def me_settings():
    username = current_user.id
    user = db.userprofiles.find_one({'username':username})
    user_profiles = user['lrsprofiles']
    
    return render_template('mysettings.html', user_profiles=user_profiles)

# Update the LRS endpoints for the user
@app.route('/me/settings/update_endpoint', methods=["POST"])
@login_required
def update_endpoint():
    username = current_user.id
    # Werkzeug returns immutabledict object when multiple forms are on page. have to copy to get values
    sf = request.form.copy()
    
    default = False
    if 'default' in sf.keys():
        default = True

    # Update profile with form input
    user = db.userprofiles.find_one({'username':username})
    for profile in user['lrsprofiles']:
        if profile['name'] == sf['name']:
            profile['endpoint'] = sf['endpoint']
            profile['username'] = sf['username']
            profile['password'] = sf['password']
            profile['auth'] = "Basic %s" % base64.b64encode("%s:%s" % (profile['username'], profile['password']))
            profile['default'] = default
        elif not profile['name'] == sf['name'] and default:
            profile['default'] = False

    db.userprofiles.update({'username':username}, user)
    return redirect(url_for('me'))

# Add an LRS endpoint to a user profile
@app.route('/me/settings/add_endpoint', methods=["POST"])
@login_required
def add_endpoint():
    username = current_user.id
    af = request.form.copy()
    user = db.userprofiles.find_one({'username':username})

    existing_names = [p['name'] for p in user['lrsprofiles']]

    # Make sure name doesn't exist already
    if not af['newname'] in existing_names:
        new_prof = {}
        default = False
        if 'newdefault' in af.keys():
            default = True

        new_prof['name'] = af['newname']
        new_prof['endpoint'] = af['newendpoint']
        new_prof['username'] = af['newusername']
        new_prof['password'] = af['newpassword']
        new_prof['auth'] = "Basic %s" % base64.b64encode("%s:%s" % (new_prof['username'], new_prof['password']))
        new_prof['default'] = default

        if default:
            for profile in user['lrsprofiles']:
                profile['default'] = False

        user['lrsprofiles'].append(new_prof)
        db.userprofiles.update({'username':username}, user)
    
    return redirect(url_for('me'))

# Load LR search page
@app.route('/lr_search', methods=["GET"])
def lr_search():
    # Get all comps/fwks/perfwks and parse id so it can be displayed
    comps = models.findCompetencies(sort='title')
    compfwks = models.findCompetencyFrameworks()
    perfwks = models.findPerformanceFrameworks()

    for c in comps:
        c['_id'] = str(c['_id'])

    for cf in compfwks:
        cf['_id'] = str(cf['_id'])

    for p in perfwks:
        p['_id'] = str(p['_id'])

    # Need to escape double quote so can pass to JS
    jcomps = json.dumps(comps).replace('"', '\\"')
    jcfwks = json.dumps(compfwks).replace('"', '\\"')
    jpfwks = json.dumps(perfwks).replace('"', '\\"')

    return render_template('lrsearch.html', search_form=SearchForm(), comps=jcomps,
        compfwks=jcfwks, perfwks=jpfwks)

# Link lr data to comp
@app.route('/link_lr_comp', methods=['POST'])
def link_lr_comp():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']

    try:
        models.updateCompetencyLR(c_id, LR_NODE + lr_uri)
    except Exception, e:
        return e.message
    return "Successfully linked competency"

# Link lr data to comp fwk
@app.route('/link_lr_cfwk', methods=['POST'])
def link_lr_cfwk():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']

    try:
        models.updateCompetencyFrameworkLR(c_id, LR_NODE + lr_uri)
    except Exception, e:
        return e.message
    return "Successfully linked competency framework"

# Linke lr data to per fwk
@app.route('/link_lr_pfwk', methods=['POST'])
def link_lr_pfwk():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']

    try:
        models.updatePerformanceFrameworkLR(c_id, LR_NODE + lr_uri)
    except Exception, e:
        return e.message
    return "Successfully linked performance framework"

# Admin reset button to clear entire db
@app.route('/admin/reset', methods=["POST"])
@check_admin
def reset_all():
    logout_user()
    models.dropAll()
    return redirect(url_for("index"))

# Admin comp reset button to clear all comp collections
@app.route('/admin/reset/comps', methods=["POST"])
@check_admin
def reset_comps():
    models.dropCompCollections()
    return redirect(url_for("index"))

# Create new competencies
@app.route('/admin/competency/new', methods=['GET', 'POST'])
@check_admin
def new_comp():
    if request.method == 'GET':
        return render_template('edit-comp.html', **{'cform': CompetencyEditForm()})
    else:
        f = CompetencyEditForm(request.form)
        if f.validate():
            models.saveCompetency(f.toDict())
            return redirect(url_for('competencies', uri=f.uri.data))
        return render_template('edit-comp.html', **{'cform': f})

# Edit competencies
@app.route('/admin/competency/edit/<objid>', methods=['GET', 'POST'])
@check_admin
def edit_comp(objid):
    if request.method == 'GET':
        obj = models.getCompetencyById(objid)
        return_dict = {'cform': CompetencyEditForm(obj=obj)}
    else:
        f = CompetencyEditForm(request.form)
        valid = f.validate()
        if valid:
            models.updateCompetencyById(objid, f.toDict())
            # redirect to comp details
            return redirect(url_for('competencies', uri=f.uri.data))
        return_dict = {'cform': f}
    return render_template('edit-comp.html', **return_dict)

# Search all competencies added to system right now
@app.route('/compsearch', methods=['GET', 'POST'])
def compsearch():
    comps = []
    if request.method == 'GET':
        return render_template('compsearch.html', comps=comps, search_form=SearchForm())
    else:
        sf = SearchForm(request.form)
        if sf.validate_on_submit():
            key = sf.search.data
            comps = models.searchComps(key)
        return render_template('compsearch.html', comps=comps, search_form=sf)        

@app.route('/check_badges', methods=['POST'])
def check_badges():
    uri = request.form.get('uri', None)
    p = performance.evaluate(uri, current_user.id)
    return Response(json.dumps(p), mimetype='application/json')
    # return render_template('check_badges.html')

@app.route('/badgeclass/issuer')
def tetris_issuer():
    return jsonify({"name": "Advanced Distributed Learning (ADL)", "url": "http://adlnet.gov"})

@app.route('/badgeclass/<perfwk_id>/<component_id>/<perf_id>')
def tetris_badge(perfwk_id, component_id, perf_id):
    b_fwk = models.findPerformanceFrameworks({'uuidurl': perfwk_id})
    if not b_fwk:
        abort(404)
    
    b_class = models.getBadgeClass(component_id, perf_id)
    if not b_class:
        abort(404)
    return b_class 

@app.route('/badgeclass/<perfwk_id>/<component_id>/<perf_id>/badge')
def tetris_badge_pic(perfwk_id, component_id, perf_id):
    b_fwk = models.findPerformanceFrameworks({'uuidurl': perfwk_id})
    if not b_fwk:
        abort(404)
    
    b_class = models.getBadgeClass(component_id, perf_id)
    if not b_class:
        abort(404)
    return url_for('static', filename='spacecat.png')


@app.route('/tetris/assertions/<ass_id>')
def tetris_assertion(ass_id):
    ass = models.getBadgeAssertion(ass_id)
    if not ass:
        abort(404)
    return ass

@app.route('/test')
def test():
    uri = "http://12.109.40.34/performance-framework/xapi/tetris"
    userid = "tom"
    # seed system with perfwk
    # objid = models.getPerformanceFramework(uri)
    competency.parseComp(uri)
    # reg user with perfwk
    models.addPerFwkToUserProfile(uri, userid)

    #### now do the performance stuff
    p = performance.evaluate(uri, userid)
    return Response(json.dumps(p), mimetype='application/json')