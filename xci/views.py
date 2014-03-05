from xci import app, competency
from xci.competency import MBCompetency as mbc
from functools import wraps
from flask import render_template, redirect, flash, url_for, request, make_response, Response
from forms import LoginForm, RegistrationForm, FrameworksForm, SettingsForm, SearchForm, CompetencyEditForm
from models import User
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from pymongo import MongoClient
from werkzeug.security import generate_password_hash
import json
import models
import requests
import pdb

login_manager = LoginManager()
login_manager.init_app(app)

mongo = MongoClient()
db = mongo.xci

def check_admin(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        person = current_user
        if not 'admin' in person.roles:
            return redirect(url_for('index'))
        return func(*args, **kwargs)
    return wrapper

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
    uri = request.args.get('uri', None)
    if uri:
        p = competency.parseComp(uri)
        try:
            return redirect(url_for("competencies"))
        except Exception as e:
            return make_response("%s<br>%s" % (str(e), p), 200)
    return render_template('home.html')
    
@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))

@app.route('/login', methods=["GET","POST"])
def login():
    if request.method == 'GET':
        return render_template('login.html', login_form=LoginForm())
    else:
        lf = LoginForm(request.form)
        if lf.validate_on_submit():
            user = User(lf.username.data, generate_password_hash(lf.password.data))
            login_user(user)
            return redirect(url_for("index"))
        else:
            return render_template("login.html", login_form=lf)

@app.route('/sign_up', methods=["GET", "POST"])
def sign_up():
    if request.method == 'GET':
        return render_template('sign_up.html', signup_form=RegistrationForm(), hide=True)
    else:
        rf = RegistrationForm(request.form)
        if rf.validate_on_submit():
            role = rf.role.data
            if role == 'admin':
                role = ['admin', 'teacher', 'student']
            elif role == 'teacher':
                role = ['teacher', 'student']
            else:
                role = ['student']

            users = db.userprofiles
            users.insert({'username': rf.username.data, 'password':generate_password_hash(rf.password.data), 'email':rf.email.data,
                'first_name':rf.first_name.data, 'last_name':rf.last_name.data, 'competencies':{}, 'compfwks':{}, 'perfwks':{}, 'lrsprofiles':[], 'roles':role})

            user = User(rf.username.data, generate_password_hash(rf.password.data))
            login_user(user)
            return redirect(url_for('index'))
        return render_template('sign_up.html', signup_form=rf, hide=True)

@app.route('/competencies')
def competencies():
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
        if mb:
            if not comp.get('edited', False) and competency.isMB(comp):
                try:
                    thexml = requests.get(competency.addXMLSuffix(comp['uri'])).text
                except:
                    thexml = mbc.toXML(comp)
            else:
                thexml = mbc.toXML(comp)
            return Response(thexml, mimetype='application/xml')
            # return render_template('comp-mb-edit.html', **d)
        else:
            return render_template('comp-details.html', **d)

    d['comps'] = models.findCompetencies()
    return render_template('competencies.html', **d)

@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
    if request.method == 'GET':
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
        ff = FrameworksForm(request.form)
        if ff.validate_on_submit():
            try:
                #add to system
                pass
            except Exception, e:
                raise e
            return_dict = {'frameworks_form': FrameworksForm()}
        else:
            return_dict = {'frameworks_form': ff}

    return_dict['cfwks'] = models.findCompetencyFrameworks()
    return render_template('frameworks.html', **return_dict)

@app.route('/perfwks', methods=["GET", "POST"])
def perfwks():
    if request.method == 'GET':
        uri = request.args.get('uri', None)
        uview = request.args.get('userview', False)
        if uri:
            d = {}
            d['uri'] = uri
            d['fwk'] = models.getPerformanceFramework(uri)
            d['userview'] = uview
            return render_template('perfwk-details.html', **d)

    d = {'pfwks':models.findPerformanceFrameworks()}
    return render_template('performancefwks.html', **d)

@app.route('/me', methods=["GET"])
@login_required
def me():
    username = current_user.id
    user = models.getUserProfile(username)
    user_comps = user['competencies'].values()
    user_fwks = user['compfwks'].values()
    user_pfwks = user['perfwks'].values()
    # user_profiles = user['lrsprofiles']

    # completed_comps = [c for c in user_comps if c['completed'] == True].count()
    completed_comps = sum(1 for c in user_comps if c.get('completed',False))
    started_comps = len(user_comps) - completed_comps   
    name = user['first_name'] + ' ' + user['last_name']

    return render_template('me.html', comps=user_comps, fwks=user_fwks, pfwks=user_pfwks, completed=completed_comps, started=started_comps, name=name, email=user['email'])

@app.route('/me/add', methods=["POST"])
@login_required
def add_comp():
    uri = request.form.get('comp_uri', None)
    userprof = models.getUserProfile(current_user.id)
    if uri:
        h = str(hash(uri))
        if not userprof.get('competencies', False):
            userprof['competencies'] = {}
        if uri and h not in userprof['competencies']:
            comp = models.getCompetency(uri)
            userprof['competencies'][h] = comp
            models.saveUserProfile(userprof, current_user.id)
    elif request.form.get('fwk_uri', False):
        fwkuri = request.form.get('fwk_uri', None)
        fh = str(hash(fwkuri))
        if not userprof.get('compfwks', False):
            userprof['compfwks'] = {}
        if fwkuri and fh not in userprof['compfwks']:
            fwk = models.getCompetencyFramework(fwkuri)
            userprof['compfwks'][fh] = fwk
            models.saveUserProfile(userprof, current_user.id)
    elif request.form.get('perfwk_uri', False):
        fwkuri = request.form.get('perfwk_uri', None)
        fh = str(hash(fwkuri))
        if not userprof.get('perfwks', False):
            userprof['perfwks'] = {}
        if fwkuri and fh not in userprof['perfwks']:
            fwk = models.getPerformanceFramework(fwkuri)
            userprof['perfwks'][fh] = fwk
            models.saveUserProfile(userprof, current_user.id)

    return redirect(url_for("me"))

@app.route('/cc')
def load_cc():
    from xci import commoncore
    commoncore.getCommonCore()
    return redirect(url_for("competencies"))

@app.route('/me/settings', methods=["GET"])
@login_required
def me_settings():
    username = current_user.id
    user = db.userprofiles.find_one({'username':username})
    user_profiles = user['lrsprofiles']
    
    return render_template('mysettings.html', user_profiles=user_profiles)

@app.route('/me/settings/update_endpoint', methods=["POST"])
@login_required
def update_endpoint():
    username = current_user.id
    #Werkzeug returns immutabledict object when multiple forms are on page. have to copy to get values
    sf = request.form.copy()
    
    default = False
    if 'default' in sf.keys():
        default = True

    user = db.userprofiles.find_one({'username':username})
    for profile in user['lrsprofiles']:
        if profile['name'] == sf['name']:
            profile['endpoint'] = sf['endpoint']
            profile['auth'] = sf['auth']
            profile['password'] = generate_password_hash(sf['password'])
            profile['default'] = default
        elif not profile['name'] == sf['name'] and default:
            profile['default'] = False

    db.userprofiles.update({'username':username}, user)

    # db.userprofiles.update({'username':username, 'lrsprofiles.name': sf['name']}, {'$set':{'name':sf['name'],'endpoint':sf['endpoint'], 'auth':sf['auth'],
    #     'password': generate_password_hash(sf['password']), 'default':default}})

    return redirect(url_for('me'))

@app.route('/me/settings/add_endpoint', methods=["POST"])
@login_required
def add_endpoint():
    username = current_user.id
    af = request.form.copy()
    user = db.userprofiles.find_one({'username':username})

    existing_names = [p['name'] for p in user['lrsprofiles']]

    if af['newname'] in existing_names:
        pass
    else:
        new_prof = {}
        default = False
        if 'newdefault' in af.keys():
            default = True

        new_prof['name'] = af['newname']
        new_prof['endpoint'] = af['newendpoint']
        new_prof['auth'] = af['newauth']
        new_prof['password'] = generate_password_hash(af['newpassword'])
        new_prof['default'] = default

        if default:
            for profile in user['lrsprofiles']:
                profile['default'] = False

        user['lrsprofiles'].append(new_prof)
        db.userprofiles.update({'username':username}, user)
    
    return redirect(url_for('me'))

@app.route('/lr_search', methods=["GET"])
def lr_search():
    comps = models.findCompetencies()
    for c in comps:
        c['id'] = str(c['_id'])
        del c['_id']

    return render_template('lrsearch.html', search_form=SearchForm(), comps=comps)

@app.route('/admin/reset', methods=["POST"])
@check_admin
def reset_all():
    logout_user()
    models.dropAll()
    return redirect(url_for("index"))

@app.route('/admin/reset/comps', methods=["POST"])
@check_admin
def reset_comps():
    models.dropCompCollections()
    return redirect(url_for("index"))

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

@app.route('/admin/competency/edit/<objid>', methods=['GET', 'POST'])
@check_admin
def edit_comp(objid):
    if request.method == 'GET':
        obj = models.getCompetencyById(objid)
        return_dict = {'cform': CompetencyEditForm(obj=obj)}
    else:
        f = CompetencyEditForm(request.form)
        valid = f.validate()
        print 'valid >>> %s' % valid
        if valid:
            #add to 
            # print "json>>>>  %s" % f.toJSON()
            models.updateCompetencyById(objid, f.toDict())
            # redirect to comp details
            return redirect(url_for('competencies', uri=f.uri.data))
        return_dict = {'cform': f}

    return render_template('edit-comp.html', **return_dict)