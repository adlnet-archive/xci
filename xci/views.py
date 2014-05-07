import base64
import json
import models
import requests
import os
import urllib
from urlparse import urlparse
from itertools import imap
from operator import itemgetter
from functools import wraps
from xci import app, competency, performance
from xci.competency import MBCompetency as mbc
from models import User
from flask import render_template, redirect, flash, url_for, request, make_response, Response, jsonify, abort, send_file
from forms import LoginForm, RegistrationForm, FrameworksForm, SettingsForm, SearchForm, CompetencyEditForm
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, current_app
from werkzeug.security import generate_password_hash
from werkzeug import secure_filename

# Init login_manager
login_manager = LoginManager()
login_manager.init_app(app)

@app.route('/badge_upload', methods=['POST'])
def badge_upload():
    # Get file and badgeimageurl that was pre-built when perfwk was created
    badge = request.files['badge']
    url = request.form['imageurl']
    uri = request.form['uri']
    componentid = request.form['componentid']

    # Make sure the file name is allowed and secure (just png for now)
    if badge and models.allowed_file(secure_filename(badge.filename)):
        parts = urlparse(url)
        path_parts = parts.path.split('/')

        badge.filename = path_parts[5]
        perflvl_id = os.path.splitext(path_parts[5])[0]
        grid_name = ':'.join(path_parts[3:6])
        try:
            saved = models.fsSaveBadgeFile(badge, grid_name)
        except Exception, e:
            return redirect(url_for('perfwks', uri=uri, error=e.message))
        else:
            perfwkobj = models.getPerformanceFramework(uri)
            for c in perfwkobj.get('components', []):
                if c['id'] == componentid:
                    for pl in c['performancelevels']:
                        if pl['id'] == perflvl_id:
                            pl['badgeuploaded'] = True
                            break
            models.updatePerformanceFramework(perfwkobj)
            return redirect(url_for('perfwks', uri=uri))
    else:
        abort(403)

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
        u_id = userobj.id
        return userobj
    else:
        u_id = user.id
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

    return render_template('home.html')
    
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
            user = User(rf.username.data)
            login_user(user)
            return redirect(url_for('index'))
        return render_template('sign_up.html', signup_form=rf, hide=True)

# Competency view
@app.route('/competencies')
def competencies():
    # Look for comp args, if none display all comps
    d = {}
    uri = request.args.get('uri', None)
    mb = request.args.get('mb', False)
    
    if uri:      
        if current_user.is_authenticated():
            user = User(current_user.id)
            comps = user.getAllComps()            
            d['registered'] = str(hash(uri)) in comps.keys()

        d['uri'] = uri
        comp = models.getCompetency(uri, objectid=True)
        d['cid'] = comp.pop('_id')
        d['comp'] = comp
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
                    models.updateCompetencyLR(d['cid'], current_app.config['LR_NODE'] + d_id + '&by_doc_ID=T')
                updated_comp = models.getCompetency(uri, objectid=True)
                d['comp'] = updated_comp

            return render_template('comp-details.html', **d)

    d['comps'] = models.findCompetencies()
    return render_template('competencies.html', **d)

@app.route('/me_competencies')
@login_required
def me_competencies():
    user = User(current_user.id)

    d = {}
    uri = request.args.get('uri', None)

    if uri:      
        d['uri'] = uri
        comp = user.getComp(uri)
        d['comp'] = comp
        return render_template('me_comp-details.html', **d)

    d['comps'] = user.getAllComps()
    return render_template('me_competencies.html', **d)


# Return competency frameworks
@app.route('/frameworks', methods=["GET", "POST"])
def frameworks():
    if request.method == 'GET':
        # Determine if requesting specific fwk or not
        uri = request.args.get('uri', None)
        if uri:
            d = {}
            if current_user.is_authenticated():         
                d['registered'] = str(hash(uri)) in User(current_user.id).profile['compfwks'].keys()

            d['uri'] = uri
            
            fwk = models.getCompetencyFramework(uri)
            for c in fwk['competencies']:
                compuri = c['uri']
                comp = models.getCompetency(compuri, objectid=True)
                if comp:
                    cid = comp['_id']
                    if 'adlnet' in compuri:
                        compuri = compuri[:7] + 'www.' + compuri[7:]
                        url = "https://node01.public.learningregistry.net/slice?any_tags=%s" % compuri
                        resp = requests.get(url)
                        ids = []
                        if resp.status_code == 200:
                            lrresults = json.loads(resp.content)
                            ids = [s['doc_ID'] for s in lrresults['documents']]
                            for d_id in ids:
                                models.updateCompetencyLR(cid, current_app.config['LR_NODE'] + d_id + '&by_doc_ID=T')

            d['fwk'] = models.getCompetencyFramework(uri)
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

# Return competency frameworks
@app.route('/me_frameworks', methods=["GET"])
@login_required
def me_frameworks():
    user = User(current_user.id)
    uri = request.args.get('uri', None)
    if uri:
        d = {}
        d['uri'] = uri
        d['fwk'] = user.getCompfwk(uri)
        return render_template('me_compfwk-details.html', **d)
    else:
        abort(404)

# Return performance frameworks
@app.route('/perfwks', methods=["GET", "POST"])
def perfwks():
    d = {}
    if request.method == 'GET':
        # Determine if asking for specific fwk or not
        uri = request.args.get('uri', None)
        d['error'] = request.args.get('error', None)
        if uri:
            if current_user.is_authenticated():           
                d['registered'] = str(hash(uri)) in User(current_user.id).profile['perfwks'].keys()

            d['uri'] = uri
            d['fwk'] = models.getPerformanceFramework(uri)
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

# Return performance frameworks
@app.route('/me_perfwks', methods=["GET"])
@login_required
def me_perfwks():
    uri = request.args.get('uri', None)
    if uri:
        d = {}
        d['uri'] = uri
        d['fwk'] = User(current_user.id).getPerfwk(uri)
        return render_template('me_perfwk-details.html', **d)
    else:
        abort(404)

# Return all data pertaining to user
@app.route('/me', methods=["GET"])
@login_required
def me():
    user = User(current_user.id)
    user_comps = user.profile['competencies'].values()
    user_fwks = user.profile['compfwks'].values()
    user_pfwks = user.profile['perfwks'].values()

    # Calculate complete competencies for users and return count
    # completed_comps = sum(1 for c in user_comps if c.get('completed',False))
    bs = []
    for c in user_comps:
        if c.get('completed',False):
            bs.append(1)
    completed_comps = len(bs)
    started_comps = len(user_comps) - completed_comps   
    name = user.first_name + ' ' + user.last_name

    mozilla_asserts = []
    for perf in user_comps:
        moz_dict = {}
        moz_dict['asserts'] = []
        moz_dict['badges'] = []
        moz_dict['title'] = perf['title']
        if 'performances' in perf:
            for p in perf['performances']:
                if 'badgeassertionuri' in p:
                    moz_dict['asserts'].append(p['badgeassertionuri'])
                if 'badgeclassimageurl' in p:
                    moz_dict['badges'].append(p['badgeclassimageurl'])
        mozilla_asserts.append(moz_dict)

    return render_template('me.html', comps=user_comps, fwks=user_fwks, pfwks=user_pfwks, completed=completed_comps, started=started_comps, name=name,
        email=user.email, mozilla_asserts=mozilla_asserts)

# Add comps/fwks/perfwks to the user
@app.route('/me/add', methods=["POST"])
@login_required
def add_comp():
    # Hashes of the uri of the comp are used to store them in the userprofile object
    user = User(current_user.id)
    if request.form.get('comp_uri', None):
        user.addComp(request.form.get('comp_uri', None))
    elif request.form.get('fwk_uri', False):
        user.addFwk(request.form.get('fwk_uri', None))
    elif request.form.get('perfwk_uri', False):
        user.addPerFwk(request.form.get('perfwk_uri', None))

    return redirect(url_for("me"))

@app.route('/me/update', methods=["POST"])
@login_required
def update_comp():
    user = User(current_user.id)
    if request.form.get('comp_uri', None):
        user.addComp(request.form.get('comp_uri', None))
    elif request.form.get('fwk_uri', False):
        user.addFwk(request.form.get('fwk_uri', None))
    elif request.form.get('perfwk_uri', False):
        user.addPerFwk(request.form.get('perfwk_uri', None))

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
    user_profiles = User(current_user.id).profile['lrsprofiles']
    return render_template('mysettings.html', user_profiles=user_profiles)

# Update the LRS endpoints for the user
@app.route('/me/settings/update_endpoint', methods=["POST"])
@login_required
def update_endpoint():
    # Werkzeug returns immutabledict object when multiple forms are on page. have to copy to get values
    sf = request.form.copy()
    default = False
    if 'default' in sf.keys():
        default = True

    # Update profile with form input
    user = User(current_user.id)
    for profile in user.profile['lrsprofiles']:
        if profile['name'] == sf['name']:
            profile['endpoint'] = sf['endpoint']
            profile['username'] = sf['auth']
            profile['password'] = sf['password']
            profile['auth'] = "Basic %s" % base64.b64encode("%s:%s" % (profile['username'], profile['password']))
            profile['default'] = default
        elif not profile['name'] == sf['name'] and default:
            profile['default'] = False

    user.save()
    return redirect(url_for('me'))

# Add an LRS endpoint to a user profile
@app.route('/me/settings/add_endpoint', methods=["POST"])
@login_required
def add_endpoint():
    af = request.form.copy()
    user = User(current_user.id)

    existing_names = [p['name'] for p in user.profile['lrsprofiles']]

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
            for profile in user.profile['lrsprofiles']:
                profile['default'] = False

        user.profile['lrsprofiles'].append(new_prof)
        user.save()
    
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

    jcomps = json.dumps(comps)
    jcfwks = json.dumps(compfwks)
    jpfwks = json.dumps(perfwks)

    return render_template('lrsearch.html', search_form=SearchForm(), comps=jcomps,
        compfwks=jcfwks, perfwks=jpfwks)

# Link lr data to comp
@app.route('/link_lr_comp', methods=['POST'])
def link_lr_comp():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']
    lr_title = request.form['lr_title']
    c_uri = request.form['c_uri']
    c_content = request.form['c_content']

    user = User(current_user.id)
    roles = user.roles

    if 'admin' in roles:
        user_role = 'admin'
    elif 'teacher' in roles:
        user_role = 'teacher'

    try:
        models.updateCompetencyLR(c_id, current_app.config['LR_NODE'] + lr_uri)
    except Exception, e:
        return e.message

    try:
        doc_id = models.sendLRParadata(lr_uri, lr_title, user_role, "competency", c_uri, c_content)
    except Exception, e:
        return "Competency updated but paradata was not sent to LR - " + e.message

    return "Successfully linked competency\n Here is the LR paradata doc_ID:" + doc_id

# Link lr data to comp fwk
@app.route('/link_lr_cfwk', methods=['POST'])
def link_lr_cfwk():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']
    lr_title = request.form['lr_title']
    c_uri = request.form['c_uri']
    c_content = request.form['c_content']

    user = User(current_user.id)
    roles = user.roles

    if 'admin' in roles:
        user_role = 'admin'
    elif 'teacher' in roles:
        user_role = 'teacher'

    try:
        models.updateCompetencyFrameworkLR(c_id, current_app.config['LR_NODE'] + lr_uri)
    except Exception, e:
        return e.message

    try:
        doc_id = models.sendLRParadata(lr_uri, lr_title, user_role, "competency framework", c_uri, c_content)
    except Exception, e:
        return "Competency framework updated but paradata was not sent to LR - " + e.message

    return "Successfully linked competency framework\n Here is the LR paradata doc_ID:" + doc_id

# Linke lr data to per fwk
@app.route('/link_lr_pfwk', methods=['POST'])
def link_lr_pfwk():
    lr_uri = request.form['lr_uri']
    c_id = request.form['c_id']
    lr_title = request.form['lr_title']
    c_uri = request.form['c_uri']
    c_content = request.form['c_content']

    user = User(current_user.id)
    roles = user.roles

    if 'admin' in roles:
        user_role = 'admin'
    elif 'teacher' in roles:
        user_role = 'teacher'

    try:
        models.updatePerformanceFrameworkLR(c_id, current_app.config['LR_NODE'] + lr_uri)
    except Exception, e:
        return e.message

    try:
        doc_id = models.sendLRParadata(lr_uri, lr_title, user_role, "performance framework", c_uri, c_content)
    except Exception, e:
        return "Performance framework updated but paradata was not sent to LR - " + e.message

    return "Successfully linked performance framework\n Here is the LR paradata doc_ID:" + doc_id

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

@app.route('/admin/competency/add_quiz/<objid>', methods=['GET', 'POST'])
@check_admin
def add_quiz_to_comp(objid):
    user = User(current_user.id)
    comp = models.getCompetencyById(objid)

    if request.method == 'GET':
        return render_template('add_quiz.html', objid=objid)
    else:
        data = models.create_questions(request.form)
        models.addCompetencyQuiz(objid, data)
        return redirect(url_for('competencies', uri=comp['uri']))
     
@app.route('/competency/quiz', methods=['GET', 'POST'])
def quiz():
    uri = request.args.get('uri', None)
    user = User(current_user.id)
    comp = models.getCompetency(uri)


    if request.method == 'GET':
        return render_template('quiz.html', uri=uri, title=comp['title'], data=comp['quiz'])
    else:    
        questions = []
        answers = []
        types = []
        responses = []

        for x in range(1,6):
            questions.append(request.form.get('questionasked' + str(x)))
            answers.append(request.form.get('answer' + str(x)))
            types.append(request.form.get('type' + str(x)))
            responses.append(request.form.get('question' + str(x)))

        actor = user.getFullAgent()
        actor_name = "%s %s" % (user.first_name, user.last_name)
        quiz_name = "adl_xci:%s" % urllib.quote_plus(comp['title'])
        display_name = comp['title'] + ' quiz'
       
        wrong, data = models.get_result_statements(responses, answers, types, questions, actor, actor_name, quiz_name, display_name)
        score = 5 - wrong

        lrs_list = []
        for prof in user.profile['lrsprofiles']:
            lrs_result_info = {'name': prof['name']}
            headers = {
                    'Authorization': prof['auth'],
                    'content-type': 'application/json',        
                    'X-Experience-API-Version': '1.0.0'
            }

            post_resp = requests.post(prof['endpoint'] + "statements", data=json.dumps(data), headers=headers, verify=False)
            lrs_result_info['status'] = post_resp.status_code
            lrs_result_info['content'] = post_resp.content

            lrs_result_info['stmts'], lrs_result_info['sens'] = models.retrieve_statements(lrs_result_info['status'],
                lrs_result_info['content'], prof['endpoint'] + "statements", headers)    
            lrs_list.append(lrs_result_info)

        return render_template('quiz_results.html', title=comp['title'], uri=comp['uri'], score=score, lrs_list=lrs_list)

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

@app.route('/static/badgeclass/issuer')
def tetris_issuer():
    return jsonify({"name": "Advanced Distributed Learning (ADL)", "url": current_app.config['DOMAIN_NAME']})

@app.route('/static/badgeclass/<perfwk_id>/<component_id>/<perf_id>')
def tetris_badge(perfwk_id, component_id, perf_id):
    # Probably a better way of doing this - serve png
    if '.png' in perf_id:
        filename = ':'.join([perfwk_id, component_id, perf_id])
        try:
            badge = models.fsGetLastVersion(filename)
        except Exception, e:
            abort(404)

        badge_file = models.fsGetByID(badge._file['_id'])
        response = make_response(badge_file.read())
        response.mimetype = badge_file.content_type
        return response
    # Serve metadata if not png
    else:
        b_fwk = models.findPerformanceFrameworks({'uuidurl': perfwk_id})
        if not b_fwk:
            abort(404)
        
        b_class = models.getBadgeClass(perfwk_id, perf_id)
        if not b_class:
            abort(404)

        return b_class 

@app.route('/view_assertions', methods=['POST'])
def view_assertions():
    uri = request.form.get('uri', None)
    name = current_user.id

    p = performance.evaluate(uri, name)
    if p:
        models.createAssertion(p, uri)

    return redirect(url_for('me'))


@app.route('/assertions/<ass_id>')
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