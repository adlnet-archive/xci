import re
import datetime
import pytz
from bson.objectid import ObjectId
from flask_login import UserMixin
from pymongo import MongoClient
from flask import jsonify

# Init db
mongo = MongoClient()
db = mongo.xci

def getBadgeClass(class_id):
    badge = db.badgeclass.find_one({'_id': ObjectId(class_id)})
    del badge['_id']
    return jsonify(badge)

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

# Update actual per fwk
def updatePerformanceFramework(json_fwk):
    val = db.perfwk.update({'uri':json_fwk['uri']}, json_fwk, manipulate=False)

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
