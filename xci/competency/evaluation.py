import requests
import json

class Evaluate(object):
    def __init__(self, user):
        super(Evaluate, self).__init__()
        self.user = user
        self.xapi = XAPIWrapper(user.profile.get('lrsprofiles', None))
    
    def check_all(self):
        comps = self.user.getCompArray()
        for c in comps:
            self.check_comp(c['uri'], update=True)

        compfwks = self.user.getCompfwkArray()
        for cf in compfwks:
            self.check_fwk(cf['uri'], update=True)

    def check_comp(self, uri, force=False, update=False):
        comp = self.user.getComp(uri)
        if not comp and update:
            self.user.addComp(uri)
            comp = self.user.getComp(uri)
        if not comp:
            return False

        if not force:
            return self.user.getComp(uri).get('completed', False)

        results = self.xapi.getstatements(
            agent=self.user.email, 
            verb='http://adlnet.gov/expapi/verbs/passed',
            activity=uri, related_activities=True)
        
        if results[0]:
            stmts = results[1].get('statements', [])
            if stmts:
                if update:
                    comp['completed'] = True
        self.user.updateComp(comp)
        return comp.get('completed', False)

    def check_fwk(self, uri, force=False, update=False):
        fwk = self.user.getCompfwk(uri)

        if not fwk and update:
            self.user.addFwk(uri)
            fwk = self.user.getCompfwk(uri)

        if not fwk:
            return False

        if not force:
            return self.user.getCompfwk(uri).get('completed', False)
                
        results = []
        for c in fwk.get('competencies', []):
            if c['type'] == 'http://ns.medbiq.org/competencyframework/v1/':
                results.append(self.check_fwk(c['uri'], force=force, update=update))
            else:
                results.append(self.check_comp(c['uri'], force=force, update=update))

        if all(results):
            if update:
                fwk['completed'] = True
                self.user.updateFwk(fwk)
            return True

        return False

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
            print r.json()
            return (True, r.json())
        return (False, r.text)

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
