import re
import datetime
import pytz
import badgebakery
import os
import base64
import requests
import gridfs
from requests.auth import HTTPBasicAuth
import json
from bson.objectid import ObjectId
from flask_login import UserMixin
from pymongo import MongoClient
from flask import jsonify, current_app
from werkzeug.security import generate_password_hash

# Init db
mongo = MongoClient()
db = mongo.xci
fs = gridfs.GridFS(db)

# Exception class for the LR
class LRException(Exception):
    pass

# Badge and assertion functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in current_app.config['ALLOWED_BADGE_EXTENSIONS']

def fsSaveBadgeFile(badge, grid_name):
    return fs.put(badge, contentType=badge.content_type, filename=grid_name)

def fsGetLastVersion(filename):
    return fs.get_last_version(filename)

def fsGetByID(_id):
    return fs.get(_id)

def getBadgeIdByName(name):
    return str(db.badgeclass.find_one({'name': name})['_id'])

def updateAssertion(_id, url):
    db.badgeassertion.update({'_id':_id}, {'$set':{'uid':str(_id)}})
    db.badgeassertion.update({'_id':_id}, {'$set':{'verify.url':url}})

def getBadgeClass(perf_id, p_id, json_resp=True):
    badge = db.badgeclass.find_one({'uuidurl': perf_id,'name': p_id})
    if not badge:
        return None
    del badge['_id']
    del badge['uuidurl']
    
    if json_resp:
        return jsonify(badge)
    else:
        return badge

def getBadgeAssertion(ass_id):
    ass = db.badgeassertion.find_one({'_id': ObjectId(ass_id)})
    if not ass:
        return None

    del ass['_id']
    return jsonify(ass)

def getAllBadgeAssertions(name):
    asses = {'assertions':[]}
    count = 0
    prof = getUserProfile(name)
    for k,v in prof['competencies'].items():
        for p in v['performances']:
            if 'badgeassertionuri' in p.keys():
                asses['assertions'].append(p['badgeassertionuri'])
                count += 1
    asses['count'] = count

    return jsonify(asses)

def createAssertion(userprof, uri):
    uuidurl = userprof['perfwks'][str(hash(uri))]['uuidurl']
    for k, v in userprof['competencies'].items():
        if 'performances' in v.keys():
            for perf in v['performances']:
                if 'badgeassertionuri' not in perf:    
                    badge_uri = getBadgeClass(uuidurl, perf['levelid'], False)['image'][:-4]
                    badgeassertion = {
                     'recipient':{
                         'type': 'email',
                         'hashed': False,
                         'identity': userprof['email']
                         },
                     'issuedOn': datetime.datetime.now(pytz.utc).isoformat(),
                     'badge': badge_uri,
                     'verify':{
                         'type': 'hosted',
                         'url': ''
                         },
                     'evidence': perf['statementurl']
                    }
                    _id = db.badgeassertion.insert(badgeassertion)
                    assertionuri = current_app.config['DOMAIN_NAME'] + '/assertions/%s' % str(_id)
                    updateAssertion(_id, assertionuri)
                    perf['badgeassertionuri'] = assertionuri
                    perf['badgeclassimageurl'] = badgeassertion['badge'] + ".png"
                    updateUserProfile(userprof, userprof['username'])

                # # Create the baked badge - for later use
                # unbaked = os.path.join(os.path.dirname(__file__), 'static/%s.png' % perf['levelid'])
                # name_encoding = base64.b64encode('%s-%s' % (perf['levelid'], userprof['email']))
                # baked_filename = '%s_%s' % (uuidurl, name_encoding)
                # baked = os.path.join(os.path.dirname(__file__), 'static/baked/%s.png' % baked_filename)
                # badgebakery.bake_badge(unbaked, baked, perf['badgeassertionuri'])
    
                # # Once baked image is created, store in mongo
                # storeBakedBadges()

# Perform actual update of profile
def updateUserProfile(profile, userid):
    db.userprofiles.update({'username':userid}, profile, manipulate=False)


# User class to montor who is logged in - inherits from userMixin class from flask_mongo
class User(UserMixin):
    def __init__(self, userid, password=None, email=None, first_name=None, last_name=None, roles=None):
        self.userprofile = UserProfile(userid, password, email, first_name, last_name, roles)
        # self.id = userid
        self.password = self.userprofile.profile['password']
        self.roles = self.userprofile.profile['roles']

    @property
    def profile(self):
        return self.userprofile.profile

    @profile.setter
    def profile(self, value):
        self.userprofile.profile = value

    @property
    def id(self):
        return self.profile['username']

    @property
    def last_name(self):
        return self.profile['last_name']

    @last_name.setter
    def last_name(self, value):
        self.profile['last_name'] = value
    
    @property
    def first_name(self):
        return self.profile['first_name']

    @first_name.setter
    def first_name(self, value):
        self.profile['first_name'] = value
    
    @property
    def email(self):
        return self.profile['email']

    @email.setter
    def email(self, value):
        self.profile['email'] = value
    
    def save(self):
        self.userprofile.save()

    def getFullAgent(self):
        return {
            "mbox" : "mailto:%s" % self.profile['email'],
            "name" : "%s %s" % (self.profile['first_name'], self.profile['last_name']),
            "objectType": "Agent"
        }

    def getComp(self, uri):
        return self.profile['competencies'][str(hash(uri))]

    def getCompArray(self):
        return self.profile['competencies'].values()

    def getAllComps(self):
        return self.profile['competencies']

    def updateComp(self, json_comp):
        self.profile['competencies'][str(hash(json_comp['uri']))] = json_comp
        self.save()
        for fwk in self.profile['compfwks'].values():
            self.updateFwkCompsWithCompletedVal(fwk, json_comp['uri'], json_comp['completed'])

    def updateFwkCompsWithCompletedVal(self, fwk, uri, completed):
        for c in fwk['competencies']: 
            if c['type'] != 'http://ns.medbiq.org/competencyframework/v1/':
                if c['uri'] == uri:
                    c['completed'] = completed
            else:
                self.updateFwkCompsWithCompletedVal(c, uri, completed)
        self.save()
    
    def getCompfwk(self, uri):
        return self.profile['compfwks'][str(hash(uri))]

    def updateFwk(self, json_comp):
        self.profile['compfwks'][str(hash(json_comp['uri']))] = json_comp
        self.save()

    def getCompfwkArray(self):
        return self.profile['compfwks'].values()

    def getPerfwk(self, uri):
        return self.profile['perfwks'][str(hash(uri))]


    # Given a URI and Userid, store a copy of the comp in the user profile
    def addComp(self, uri):
        h = str(hash(uri))
        if not self.profile.get('competencies', False):
            self.profile['competencies'] = {}
        if uri and h not in self.profile['competencies']:
            comp = getCompetency(uri)
            if comp:
                self.profile['competencies'][h] = comp
            self.save()

    def addFwk(self, uri):
        fh = str(hash(uri))
        if not self.profile.get('compfwks', False):
            self.profile['compfwks'] = {}
        if uri and fh not in self.profile['compfwks']:
            fwk = getCompetencyFramework(uri)
            self.profile['compfwks'][fh] = fwk
            for c in fwk['competencies']:
                if c['type'] == "http://ns.medbiq.org/competencyframework/v1/":
                    self.addFwk(c['uri'])
                else:
                    self.addComp(c['uri'])
            self.save()

    def addPerFwk(self, uri):
        fh = str(hash(uri))
        if not self.profile.get('perfwks', False):
            self.profile['perfwks'] = {}
        if uri and fh not in self.profile['perfwks']:
            fwk = getPerformanceFramework(uri)
            self.profile['perfwks'][fh] = fwk
            # find the competency object uri for each component and add it to the user's list of competencies
            for curi in (x['entry'] for b in fwk.get('components', []) for x in b.get('competencies', []) if x['type'] != "http://ns.medbiq.org/competencyframework/v1/"):
                self.addComp(curi)
            self.save()


class UserProfile():
    def __init__(self, userid, password=None, email=None, first_name=None, last_name=None, roles=None):
        self.userid = userid
        self._profile = db.userprofiles.find_one({'username':userid})
        # make one if it didn't return a profile
        if not self._profile:
            db.userprofiles.insert({'username': userid, 'password':generate_password_hash(password), 
                                    'email':email, 'first_name':first_name, 'last_name':last_name, 
                                    'competencies':{}, 'compfwks':{}, 'perfwks':{}, 'lrsprofiles':[], 
                                    'roles':roles})

            self._profile = db.userprofiles.find_one({'username':userid})

    @property
    def profile(self):
        return self._profile

    @profile.setter
    def profile(self, value):
        self._profile = self.save(value)

    # Update or insert user profile if id is given
    def save(self, profile=None):
        if profile:
            self._profile = profile
        db.userprofiles.update({'username':self.userid}, self._profile, manipulate=False)




# LR functions
# Update all comp fwks
def updateCompetencyFrameworkLR(cfwk_id, lr_uri):
    db.compfwk.update({'_id': ObjectId(cfwk_id)}, {'$addToSet':{'lr_data':lr_uri}})
    updateUserFwkById(cfwk_id)

#  Update all per fwks
def updatePerformanceFrameworkLR(pfwk_id, lr_uri):
    db.perfwk.update({'_id': ObjectId(pfwk_id)}, {'$addToSet':{'lr_data':lr_uri}})
    updateUserPfwkById(pfwk_id)

# Update the comp with new LR data-calls other LR updates
def updateCompetencyLR(c_id,lr_uri):
    if isinstance(c_id, basestring):
        c_id = ObjectId(c_id)

    db.competency.update({'_id': c_id}, {'$addToSet':{'lr_data':lr_uri}})
    comp_uri = db.competency.find_one({'_id': c_id})['uri']
    updateUserCompLR(comp_uri, lr_uri)
    updateCompInFwksLR(comp_uri, lr_uri)

# Update the comp in all users
def updateUserCompLR(c_uri, lr_uri):
    h = str(hash(c_uri))
    set_field = 'competencies.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$addToSet':{set_field+'.lr_data': lr_uri}}, multi=True)

# Updates all comp fwks that contain that comp
def updateCompInFwksLR(c_uri, lr_uri):
    # Remove this field in comp before updating the fwk
    db.compfwk.update({'competencies':{'$elemMatch':{'uri':c_uri}}}, {'$addToSet': {'competencies.$.lr_data': lr_uri }}, multi=True)
    updateUserFwkByURILR(c_uri, lr_uri)

# Updates all comps in fwks that are in the userprofiles
def updateUserFwkByURILR(c_uri, lr_uri):
    comp = db.competency.find_one({'uri': c_uri})
    if not comp['type'] == 'commoncoreobject':
        try:
            parents = comp['relations']['childof']
        except KeyError:
            parents = []

        # For each parent fwk the comp is in, update it in that userprofile
        for uri in parents:
            fwk = db.compfwk.find({'uri': uri})[0]
            h = str(hash(uri))
            set_field = 'compfwks.' + h + '.competencies'
            db.userprofiles.update({set_field:{'$elemMatch':{'uri':c_uri}}}, {'$addToSet':{set_field + '.$.lr_data': lr_uri}}, multi=True)

def sendLRParadata(lr_uri, lr_title, user_role, c_type, c_uri, c_content): 
    date = datetime.datetime.now(pytz.utc).isoformat()
    paradata = {
        "documents": [
            {
                "TOS": {
                    "submission_TOS": "http://www.learningregistry.org/tos/cc0/v0-5/"
                },
                "doc_type": "resource_data",
                "doc_version": "0.23.0",
                "resource_data_type": "paradata",
                "active": True,
                "identity": {
                    "owner": "",
                    "submitter": "ADL",
                    "submitter_type": "agent",
                    "signer": "ADL",
                    "curator": ""
                },
                "resource_locator": lr_uri,
                "payload_placement": "inline",
                "payload_schema": [
                    "LR Paradata 1.0"
                ],
                "resource_data": {
                    "activity":{
                        "actor":{
                            "description": ["ADL XCI " + user_role, lr_title],
                            "objectType": user_role
                        },
                        "verb":{
                            "action": "matched",
                            "date": date,
                            "context":{
                                "id":current_app.config['DOMAIN_NAME'],
                                "description":"ADL's XCI project",
                                "objectType": "Application"
                            }
                        },
                        "object":{
                            "id": lr_uri
                        },
                        "related":[{
                            "objectType": c_type,
                            "id": c_uri,
                            "content": c_content
                            }],
                        "content": "A resource found at "+lr_uri+" was matched to the "+c_type+" with ID "+c_uri+" by an "+user_role+" on "+current_app.config['DOMAIN_NAME']+" system on "+date
                    }
                }
            }
        ]
    }
    r = requests.post(current_app.config['LR_PUBLISH_ENDPOINT'], data=json.dumps(paradata), headers={"Content-Type":"application/json"},
        auth=HTTPBasicAuth(current_app.config['LR_PUBLISH_NAME'], current_app.config['LR_PUBLISH_PASSWORD']), verify=False)
    
    if r.status_code != 200:
        message = json.loads(r.content)['message']
        raise LRException(message)
    else:
        return json.loads(r.content)['document_results'][0]['doc_ID']









# General comp/fwk functions
# Use on search comp page-searches for search keyword in comp titles
def searchComps(key):
    regx = re.compile(key, re.IGNORECASE)
    return db.competency.find({"title": regx})

# Update or insert competency depending if it exists
def saveCompetency(json_comp):
    if not json_comp.get('lastmodified', False):
        json_comp['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
    if getCompetency(json_comp['uri']):
        updateCompetency(json_comp)
    else:
        db.competency.insert(json_comp, manipulate=False)

# Update all comp fwks in the user by id
def updateUserFwkById(cfwk_id):
    fwk = db.compfwk.find_one({'_id': ObjectId(cfwk_id)})
    h = str(hash(fwk['uri']))
    set_field = 'compfwks.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field:fwk}}, multi=True)

# Update all per fwks in the user by id
def updateUserPfwkById(pfwk_id):
    fwk = db.perfwk.find_one({'_id': ObjectId(pfwk_id)})
    h = str(hash(fwk['uri']))
    set_field = 'perfwks.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field:fwk}}, multi=True)

# Update the competency by uri
def updateCompetency(json_comp):
    db.competency.update({'uri':json_comp['uri']}, json_comp, manipulate=False)

# Get the competency based on uri
def getCompetency(uri, objectid=False):
    if objectid:
        return db.competency.find_one({'uri':uri})
    return db.competency.find_one({'uri':uri}, {'_id':0})

# Update comp by id
def updateCompetencyById(cid, comp):
    comp['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
    db.competency.update({'_id': ObjectId(cid)}, comp, manipulate=False)

# Get comp by id
def getCompetencyById(cid, objectid=False):
    if objectid:
        return db.competency.find_one({'_id': ObjectId(cid)})
    return db.competency.find_one({'_id': ObjectId(cid)}, {'_id':0})

# Just return one comp
def findoneComp(d):
    return db.competency.find_one(d)

# Return comps based on search param and sort
def findCompetencies(d=None, sort=None, asc=1):
    if sort:
        return [x for x in db.competency.find(d).sort(sort, asc)]
    return [x for x in db.competency.find(d)]

# return comp fwks based on search param
def findCompetencyFrameworks(d=None):
    return [x for x in db.compfwk.find(d)]

# Update or create comp fwk based on uri
def saveCompetencyFramework(json_fwk):
    if getCompetencyFramework(json_fwk['uri']):
        updateCompetencyFramework(json_fwk)
    else:
        db.compfwk.insert(json_fwk, manipulate=False)

# Update actual comp
def updateCompetencyFramework(json_fwk):
    db.compfwk.update({'uri':json_fwk['uri']}, json_fwk, manipulate=False)

# Return one comp fwk based on uri
def getCompetencyFramework(uri, objectid=False):
    if objectid:
        return db.compfwk.find_one({'uri':uri})
    return db.compfwk.find_one({'uri': uri}, {'_id':0})

# Update or create per fwk
def savePerformanceFramework(json_fwk):
    if getPerformanceFramework(json_fwk['uri']):
        updatePerformanceFramework(json_fwk)
    else:
        db.perfwk.insert(json_fwk, manipulate=False)

        # Create badgeclasses when created the perfwk
        for c in json_fwk['components']:
            for p in c['performancelevels']:
                badgeclass = {
                    "name": p['id'],
                    "description": p['description'],
                    "image": '%s/%s/%s/%s/%s.png' % (current_app.config['DOMAIN_NAME'], current_app.config['BADGE_UPLOAD_FOLDER'], json_fwk['uuidurl'], c['id'], p['id']),
                    "criteria": json_fwk['uri'] + '.xml',
                    "issuer": '%s/%s/issuer' % (current_app.config['DOMAIN_NAME'], current_app.config['BADGE_UPLOAD_FOLDER']),
                    'uuidurl': json_fwk['uuidurl']
                }
                db.badgeclass.insert(badgeclass)
                p['badgeclassimage'] = badgeclass['image']

        # Update the perfwk wiht the badgeclassimage fields
        updatePerformanceFramework(json_fwk)

# Update actual per fwk
def updatePerformanceFramework(json_fwk):
    val = db.perfwk.update({'uri':json_fwk['uri']}, json_fwk, manipulate=False)
    pfwk_id = db.perfwk.find_one({'uri':json_fwk['uri']})['_id']
    updatePerfFwkUserProfile(pfwk_id)    

def updatePerfFwkUserProfile(pfwk_id):
    fwk = db.perfwk.find_one({'_id': pfwk_id})
    h = str(hash(fwk['uri']))
    set_field = 'perfwks.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field:fwk}}, multi=True)

# Get one per fwk
def getPerformanceFramework(uri, objectid=False):
    if objectid:
        return db.perfwk.find_one({'uri':uri})
    return db.perfwk.find_one({'uri':uri}, {'_id':0})

# Return per fwk based on search criteria
def findPerformanceFrameworks(d=None):
    return [x for x in db.perfwk.find(d)]

# Use on search comp page-searches for search keyword in comp titles
def searchComps(key):
    regx = re.compile(key, re.IGNORECASE)
    return db.competency.find({"title": regx})




def checkUsernameExists(username):
    return db.userprofiles.find_one({'username':username}) is not None

def checkEmailExists(email):
    return db.userprofiles.find_one({'email':email}) is not None




def create_questions(form):
    data = []
    q_dict = {}
    for i in range(1,11):
        st_i = str(i)
        q_dict = {}
        q_dict['type'] = form.get('types' + st_i)
        q_dict['question'] = form.get('question' + st_i + 'text')
        
        if q_dict['type'] == 'short answer':
            q_dict['correct'] = form.get('question' + st_i + 'answer').split(' ')
        elif q_dict['type'] == 'true/false':
            q_dict['correct'] = form.get('question' + st_i + 'answer') in ['True', 'true']
            q_dict['answers'] = [True, False]
        else:
            q_dict['correct'] = form.get('question' + st_i + 'answer')
            q_dict['answers'] = form.get('question' + st_i + 'choices').strip().split(',')

        data.append(q_dict)
    return data

def grade_results(types, answers, responses, data):
    wrong = 0
    for x in range(0,5):
        if types[x] == 'true/false':
            if answers[x] != responses[x]:
                data[x+1]['result']['success'] = False
                wrong += 1
        elif types[x] == 'choice':
            if answers[x].strip() != responses[x].strip():
                data[x+1]['result']['success'] = False
                wrong += 1
        else:
            if not set(answers[x].lower().strip().split(",")).issubset([str(i).lower().strip() for i in responses[x].split(" ")]):
                data[x+1]['result']['success'] = False
                wrong += 1
    
    return wrong, data

def retrieve_statements(status, post_content, endpoint, headers):
    stmts = []
    jstmts = []
    sens = []
    if status == 200:
        content = json.loads(post_content)

        for x in range(0,7):
            stmts.append(requests.get(endpoint + '?statementId=%s' % content[x], headers=headers, verify=False).content)
            jstmts.append(json.loads(stmts[x]))
        
        sens.append("{0} {1} {2}".format(jstmts[0]['actor']['name'], jstmts[0]['verb']['display']['en-US'], jstmts[0]['object']['definition']['name']['en-US']))
        for x in range(1, 6):
            sens.append("{0} {1} {2} ({3}) with {4}. (Answer was {5})".format(jstmts[x]['actor']['name'], jstmts[x]['verb']['display']['en-US'],
                jstmts[x]['object']['definition']['name']['en-US'], jstmts[x]['object']['definition']['description']['en-US'], jstmts[x]['result']['response'],
                jstmts[x]['result']['extensions']['answer:correct_answer']))
        sens.append("{0} {1} {2}".format(jstmts[6]['actor']['name'], jstmts[6]['verb']['display']['en-US'], jstmts[6]['object']['definition']['name']['en-US']))
    return stmts, sens

def get_result_statements(responses, answers, types, questions, actor, actor_name, quiz_name, display_name, comp_uri):
    data = [
            {
                'actor': actor,
                'verb': {'id': 'http://adlnet.gov/expapi/verbs/attempted', 'display':{'en-US': 'attempted'}},
                'object':{'id':quiz_name,
                    'definition':{'name':{'en-US':display_name}}}
            }
        ]

    for x in range(0,5):
        data.append({
            'actor': actor,
            'verb': {'id': 'http://adlnet.gov/expapi/verbs/answered', 'display':{'en-US': 'answered'}},
            'object':{'id':quiz_name + '_question' + str(x+1), 'definition':{'name':{'en-US':display_name + ' question' + str(x+1)}, 'description':{'en-US':questions[x]}}}, 
            'context':{'contextActivities':{'parent':[{'id': quiz_name}]}},
            'result':{'success': True, 'response': responses[x],'extensions': {'answer:correct_answer': answers[x]}}
            })

    wrong, data = grade_results(types, answers, responses, data)
    data.append({
                'actor': actor,
                'verb': {'id': 'http://adlnet.gov/expapi/verbs/passed', 'display':{'en-US': 'passed'}},
                'object':{'id':quiz_name, 'definition':{'name':{'en-US':display_name}}},
                'result':{'score':{'min': 0, 'max': 5, 'raw': 5 - wrong}},
                'context':{'contextActivities':{'other':[{'id': comp_uri}]}}
                })
    
    if wrong >= 2:
        data[6]['verb']['id'] = 'http://adlnet.gov/expapi/verbs/failed'
        data[6]['verb']['display']['en-US'] = 'failed'
    return wrong, data








# Update the comp with quiz - calls other updates
def addCompetencyQuiz(c_id, data):
    db.competency.update({'_id': ObjectId(c_id)}, {'$set':{'quiz':data}})
    comp_uri = db.competency.find_one({'_id': ObjectId(c_id)})['uri']
    updateUserCompQuiz(comp_uri, data)
    updateCompInFwksQuiz(comp_uri, data)

# Update the comp in all users
def updateUserCompQuiz(c_uri, data):
    h = str(hash(c_uri))
    set_field = 'competencies.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field+'.quiz': data}}, multi=True)

# Updates all comp fwks that contain that comp
def updateCompInFwksQuiz(c_uri, data):
    db.compfwk.update({'competencies':{'$elemMatch':{'uri':c_uri}}}, {'$set': {'competencies.$.quiz': data }}, multi=True)
    updateUserFwkByURIQuiz(c_uri, data)

# Updates all comps in fwks that are in the userprofiles
def updateUserFwkByURIQuiz(c_uri, data):
    comp = db.competency.find_one({'uri': c_uri})
    if not comp['type'] == 'commoncoreobject':
        try:
            parents = comp['relations']['childof']
        except KeyError:
            parents = []

        # For each parent fwk the comp is in, update it in that userprofile
        for uri in parents:
            fwk = db.compfwk.find({'uri': uri})[0]
            h = str(hash(uri))
            set_field = 'compfwks.' + h + '.competencies'
            db.userprofiles.update({set_field:{'$elemMatch':{'uri':c_uri}}}, {'$set':{set_field + '.$.quiz': data}}, multi=True)


# Admin reset functions
# Drop all of the comp collections
def dropCompCollections():
    db.drop_collection('competency')
    db.drop_collection('compfwk')
    db.drop_collection('perfwk')
    for u in db.userprofiles.find():
        u['competencies'] = {}
        u['perfwks'] = {}
        u['compfwks'] = {}
        updateUserProfile(u, u['username'])

# Drop the database
def dropAll():
    return mongo.drop_database(db)
