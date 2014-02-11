from flask_login import UserMixin
from pymongo import MongoClient

mongo = MongoClient()
db = mongo.xci

class User(UserMixin):
    def __init__(self, userid, password):
        self.id = userid
        self.password = password

    def get_id(self):
        try:
            user = db.userprofiles.find_one({"username":self.id})
            return unicode(self.id)
        except Exception, e:
            raise e

def saveCompetency(json_comp):
    if getCompetency(json_comp['uri']):
        updateCompetency(json_comp)
    else:
        db.competency.insert(json_comp, manipulate=False)

def updateCompetency(json_comp):
    db.competency.update({'uri':json_comp['uri']}, json_comp, manipulate=False)

def getCompetency(uri, objectid=False):
    if objectid:
        return db.competency.find_one({'uri':uri})
    return db.competency.find_one({'uri':uri}, {'_id':0})

def findoneComp(d):
    return db.competency.find_one(d)

def findCompetencies(d=None):
    return [x for x in db.competency.find(d)]

def saveCompetencyFramework(json_fwk):
    if getCompetencyFramework(json_fwk['uri']):
        updateCompetencyFramework(json_fwk)
    else:
        db.compfwk.insert(json_fwk, manipulate=False)

def updateCompetencyFramework(json_fwk):
    db.compfwk.update({'uri':json_fwk['uri']}, json_fwk, manipulate=False)

def getCompetencyFramework(uri):
    return db.compfwk.find_one({'uri':uri})

def savePerformanceFramework(json_fwk):
    if getPerformanceFramework(json_fwk['uri']):
        updatePerformanceFramework(json_fwk)
    else:
        db.perfwk.insert(json_fwk, manipulate=False)

def updatePerformanceFramework(json_fwk):
    print '-------   updating   -------------'
    print 'uri: %s' % json_fwk['uri']
    print 'count: %s' % db.perfwk.count()
    val = db.perfwk.update({'uri':json_fwk['uri']}, json_fwk, manipulate=False)
    print '\n'
    print val
    print '\ncount (after update): %s\n\n-----------------' % db.perfwk.count()

def getPerformanceFramework(uri):
    return db.perfwk.find_one({'uri':uri})
