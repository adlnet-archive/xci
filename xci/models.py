import re
import datetime
import pytz
import badgebakery
import os
import base64
import requests
from requests.auth import HTTPBasicAuth
import json
from bson.objectid import ObjectId
from flask_login import UserMixin
from pymongo import MongoClient
from flask import jsonify, current_app

# Init db
mongo = MongoClient()
db = mongo.xci

class LRException(Exception):
    pass

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





# User class to montor who is logged in - inherits from userMixin class from flask_mongo
class User(UserMixin):
    def __init__(self, userid, password):
        self.id = userid
        self.password = password
        self.roles = db.userprofiles.find_one({"username": self.id})['roles']

    # Get the userprofile from the db based on id
    def get_id(self):
        try:
            user = db.userprofiles.find_one({"username":self.id})
            return unicode(self.id)
        except Exception, e:
            raise e

def getFullAgent(userprofile):
    return {
        "mbox" : "mailto:%s" % userprofile['email'],
        "name" : "%s %s" % (userprofile['first_name'], userprofile['last_name'])
    }

# Return one userprofile based on id
def getUserProfile(userid):
    return db.userprofiles.find_one({'username':userid})

def getPerfwkFromUserProfile(prof, uri):
    return prof['perfwks'][str(hash(uri))]

def getCompfwkFromUserProfile(prof, uri):
    return prof['compfwks'][str(hash(uri))]

def getCompFromUserProfile(prof, uri):
    return prof['competencies'][str(hash(uri))]

def GetAllCompsFromUserProfile(prof):
    return prof['competencies']

# Update or insert user profile if id is given
def saveUserProfile(profile, userid=None):
    if userid:
        updateUserProfile(profile, userid)
    else:
        db.userprofiles.insert(profile)

# Perform actual update of profile
def updateUserProfile(profile, userid):
    db.userprofiles.update({'username':userid}, profile, manipulate=False)

# Given a URI and Userid, store a copy of the comp in the user profile
def addCompToUserProfile(uri, userid, userprof=None):
    if not userprof:
        userprof = getUserProfile(userid)
    h = str(hash(uri))
    if not userprof.get('competencies', False):
        userprof['competencies'] = {}
    if uri and h not in userprof['competencies']:
        comp = getCompetency(uri)
        userprof['competencies'][h] = comp
        saveUserProfile(userprof, userid)

# Given a URI and Userid, store a copy of the framework and comps in user profile
def addFwkToUserProfile(uri, userid):
    userprof = getUserProfile(userid)
    fh = str(hash(uri))
    if not userprof.get('compfwks', False):
        userprof['compfwks'] = {}
    if uri and fh not in userprof['compfwks']:
        fwk = getCompetencyFramework(uri)
        userprof['compfwks'][fh] = fwk
        for c in fwk['competencies']:
            addCompToUserProfile(c['uri'], userid, userprof)
        saveUserProfile(userprof, userid)

# Given URI and User id, store performance fwk, comp fwk, and comps in user profile
def addPerFwkToUserProfile(uri, userid):
    userprof = getUserProfile(userid)
    fh = str(hash(uri))
    if not userprof.get('perfwks', False):
        userprof['perfwks'] = {}
    if uri and fh not in userprof['perfwks']:
        fwk = getPerformanceFramework(uri)
        userprof['perfwks'][fh] = fwk
        # find the competency object uri for each component and add it to the user's list of competencies
        for curi in (x['entry'] for b in fwk.get('components', []) for x in b.get('competencies', []) if x['type'] != "http://ns.medbiq.org/competencyframework/v1/"):
            addCompToUserProfile(curi, userid, userprof)
        saveUserProfile(userprof, userid)

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

# Updates all comps in fwks that are in the userprofiles
def updateUserFwkByComp(comp):
    if not comp['type'] == 'commoncoreobject':
        try:
            parents = comp['relations']['childof']
        except KeyError:
            parents = []

        # For each parent fwk the comp is in, update it in that userprofile
        for uri in parents:
            fwk = db.compfwk.find({'uri': uri})[0]
            h = str(hash(uri))
            set_field = 'compfwks.' + h
            db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field: fwk}}, multi=True)

# Updates all comp fwks that contain that comp
def updateCompInFwks(comp):
    # Remove this field in comp before updating the fwk
    db.compfwk.update({'competencies':{'$elemMatch':{'uri':comp['uri']}}}, {'$set': {'competencies.$': comp}}, multi=True)
    updateUserFwkByComp(comp)

# Update the comp in all users
def updateUserComp(comp):
    h = str(hash(comp['uri']))
    set_field = 'competencies.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field: comp}}, multi=True)

# Update the comp with new LR data-calls other LR updates
def updateCompetencyLR(c_id,lr_uri):
    if isinstance(c_id, basestring):
        c_id = ObjectId(c_id)

    db.competency.update({'_id': c_id}, {'$addToSet':{'lr_data':lr_uri}})
    comp = db.competency.find({'_id': c_id})[0]
    del comp['_id']
    updateUserComp(comp)
    updateCompInFwks(comp)

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


# Update all comp fwks in the user by id
def updateUserFwkById(cfwk_id):
    fwk = db.compfwk.find_one({'_id': ObjectId(cfwk_id)})
    h = str(hash(fwk['uri']))
    set_field = 'compfwks.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field:fwk}}, multi=True)

# Update all comp fwks
def updateCompetencyFrameworkLR(cfwk_id, lr_uri):
    db.compfwk.update({'_id': ObjectId(cfwk_id)}, {'$addToSet':{'lr_data':lr_uri}})
    updateUserFwkById(cfwk_id)

# Update all per fwks in the user by id
def updateUserPfwkById(pfwk_id):
    fwk = db.perfwk.find_one({'_id': ObjectId(pfwk_id)})
    h = str(hash(fwk['uri']))
    set_field = 'perfwks.' + h
    db.userprofiles.update({set_field:{'$exists': True}}, {'$set':{set_field:fwk}}, multi=True)

#  Update all per fwks
def updatePerformanceFrameworkLR(pfwk_id, lr_uri):
    db.perfwk.update({'_id': ObjectId(pfwk_id)}, {'$addToSet':{'lr_data':lr_uri}})
    updateUserPfwkById(pfwk_id)

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
                    "image": '%s/%s/%s/%s/%s.png' % (current_app.config['DOMAIN_NAME'], current_app.config['UPLOAD_FOLDER'], json_fwk['uuidurl'], c['id'], p['id']),
                    "criteria": json_fwk['uri'] + '.xml',
                    "issuer": '%s/%s/issuer' % (current_app.config['DOMAIN_NAME'], current_app.config['UPLOAD_FOLDER']),
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

# Drop all of the comp collections
def dropCompCollections():
    db.drop_collection('competency')
    db.drop_collection('compfwk')
    db.drop_collection('perfwk')

# Drop the database
def dropAll():
    return mongo.drop_database(db)
