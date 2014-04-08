import json
import models
import requests
import urllib
from flask import current_app

evals = {"http://12.109.40.34/performance-framework/xapi/tetris": 'TetrisPerformanceEval'}

def evaluate(uri, username):
    if uri not in evals.keys():
        raise UnknownPerformanceURI("The URI [%s] has no known performance evaluation" % uri)
    return globals()[evals[uri]](uri, username).evaluate()    

class PerfEval(object):

    def __init__(self, uri, username):
        super(PerfEval, self).__init__()
        self.uri = uri
        self.username = username
        self._config()

    def _config(self):
        self.fwkobj = models.getPerformanceFramework(self.uri)
        self.userobj = models.getUserProfile(self.username)
        self.actor = urllib.quote_plus('{"mbox": "mailto:%s"}' % self.userobj['email'])
        # tetris doesn't use expapi
        self.verb = 'http://adlnet.gov/xapi/verbs/completed'
        self.query_string = '?agent={0}&verb={1}&activity={2}&related_activities={3}'
        if self.userobj['lrsprofiles']:
            self.profiles = self.userobj['lrsprofiles']
        else:
            self.profiles = [current_app.config['DEFAULT_PROFILE']]

    # override
    def evaluate(self):
        return None

    def _getStatements(self):
        allstmts = []
        for o in (c['objectid'] for c in self.fwkobj['linked_content']):
            allstmts.extend(self._requestStatments(o))
        return allstmts

    def _requestStatments(self, objuri):
        stmts = []
        for prof in self.profiles:
            query = self.query_string.format(self.actor, self.verb, objuri, 'true')
            url = prof['endpoint'] + "statements" + query
            print url
            get_resp = requests.get(url, headers=current_app.config['HEADERS'], verify=False)
            
            if get_resp.status_code != 200:
                print "got an error from performance.getStatements: %s" % get_resp.content
                return []

            stmts.extend(json.loads(get_resp.content)['statements'])
        return stmts

class UnknownPerformanceURI(Exception):
    pass

class TetrisPerformanceEval(PerfEval):
    
    def __init__(self, uri, username):
        super(TetrisPerformanceEval, self).__init__(uri, username)

    def evaluate(self):
        stmts = self._getStatements()
        levels = []
        lines = []
        scores = []
        times = []
        for s in stmts:
            levels.append(s['result']['extensions']['ext:level'])
            lines.append(s['result']['extensions']['ext:lines'])
            scores.append(s['result']['score']['raw'])
            times.append(s['result']['extensions']['ext:time'])
        
        val = None
        if lines:
            val = self.update(lines, 'comp_lines')
        
        if levels:
            val = self.update(levels, 'comp_levels')
        
        if scores:
            val = self.update(scores, 'comp_scores')
        
        if times:
            val = self.update(times, 'comp_times')

        del val['_id']
        return val

    def getComponent(self, compid):
        for com in self.fwkobj['components']:
            if com['id'] == compid:
                return com
        return None

    def update(self, valarr, componentid):
        comp = self.getComponent(componentid)
        lvlmax = max(valarr)
        compuri = self.getCompURIFromPFWK(comp)
        perfs = self.getUserTetrisCompPerformances(compuri)
        existing = [p['levelid'] for p in perfs]
        for plvl in comp['performancelevels']:
            if plvl['id'] in existing:
                continue
            if lvlmax >= int(plvl['score']['singlevalue']):
                p = {}
                p['entry'] = self.uri
                p['levelid'] = plvl['id']
                p['leveldescription'] = plvl['description']
                p['levelscore'] = plvl['score']['singlevalue']
                p['score'] =  lvlmax
                perfs.append(p)
        return self.saveUserTetrisCompPerformances(compuri, perfs)

    def getCompURIFromPFWK(self, comp):
        for c in comp['competencies']:
            if c.get('type', "") == "http://ns.medbiq.org/competencyobject/v1/":
                return c['entry']

    def getUserTetrisCompPerformances(self, compuri):
        c = self.userobj['competencies'].get(str(hash(compuri)), None)
        if c:
            return c.get('performances', [])

    def saveUserTetrisCompPerformances(self, compuri, perfs):
        c = self.userobj['competencies'].get(str(hash(compuri)), None)
        if c:
            c['performances'] = perfs
            models.saveUserProfile(self.userobj, self.username)
            return self.userobj
        return None
