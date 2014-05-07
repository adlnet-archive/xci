import requests
import json

class Evaluate(object):
    def __init__(self, user):
        super(Evaluate, self).__init__()
        self.user = user
    
    def check_all(self):
        comps = user.getCompArray()
        compfwks = user.getCompfwkArray()

    def check_one(self, uri, force=False):
        pass

class XAPIWrapper(object):
    def __init__(self, lrsprofiles):
        super(XAPIWrapper, self).__init__()
        self.profiles = lrsprofiles

    def getstatements(self, lrsprofile=None, agent=None, verb=None, 
                      activity=None, registration=None, 
                      related_activities=False, related_agents=False, 
                      since=None, until=None, limit=0):
        profile = lrsprofile if lrsprofile else self.getdefaultprofile()
        url = '%s%s' % (profile['endpoint'], 'statements')
        payload = self.getParams(agent, verb, activity, registration, 
                            related_activities, related_agents,
                            since, until, limit)

        r = requests.get(url, params=payload, headers=self.getheaders(profile), verify=False)
        print "xci.competency.evaluation.XAPIWrapper.getstatements:: url: %s" % r.url
        if r.status_code == requests.codes.ok:
            return (r.status_code, r.json())
        return (r.status_code, r.text)

    def getdefaultprofile(self):
        for p in self.profiles:
            if p.get('default', False):
                return p
        raise NoLRSConfigured('no default lrs configured.. set one in your user profile')

    def getheaders(self, profile):
        return {        
                'Authorization': profile['auth'],
                'content-type': 'application/json',        
                'X-Experience-API-Version': '1.0.0'
                }

    def getParams(self, agent=None, verb=None, 
                  activity=None, registration=None, 
                  related_activities=False, related_agents=False, 
                  since=None, until=None, limit=0):
        p = {}
        if agent:
            if isinstance(agent, basestring):
                agent = {"mbox": agent if 'mailto:' in agent else 'mailto:%s' % agent}
            p['agent'] = json.dumps(agent)
        if verb:
            p['verb'] = verb
        if activity:
            p['activity'] = activity
        if registration:
            p['registration'] = registration
        if related_activities:
            p['related_activities'] = related_activities
        if related_agents:
            p['related_agents'] = related_agents
        if since:
            p['since'] = since
        if until:
            p['until'] = until
        if limit > 0:
            p['limit'] = limit
        return p

class NoLRSConfigured(Exception):
    pass
