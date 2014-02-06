import requests
import json
import datetime
import pytz

from xci import models

import xml.etree.ElementTree as ET

CCObjectType = 'commoncoreobject'

def getccj():
    print 'getting json'
    res = requests.get("http://s3.amazonaws.com/asnstatic/data/manifest/D10003FB.json").json()
    # import pdb
    # pdb.set_trace()
    print 'gonna loop and save'
    for s in res:
        with open('./json/%s.json' % getfn(s['text']), 'w') as f:
            json.dump(s, f, indent=4)

def getfn(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    
    return ''.join(c for c in s if c in valid_chars)

def getCommonCore():
    parts = ["http://www.corestandards.org/Math.xml",
             "http://www.corestandards.org/ELA-Literacy.xml"]
    for p in parts:
        try:
            res = requests.get(p).text
        except Exception, e:
            print e
            return None
        
        try:
            saveCCXMLinDB(ET.fromstring(res))
        except Exception, e:
            print e
            return None


def saveCCXMLinDB(thexml):
    for item in thexml.iter('LearningStandardItem'):
        itemj = {}
        sc = gettitle(item)
        if not sc:
            continue

        itemj['title'] = sc
        itemj['desciption'] = getdescription(item)
        itemj['uri'] = geturi(item)
        itemj['ids'] = getids(item)
        itemj['type'] = CCObjectType
        itemj['levels'] = getlevels(item)
        itemj['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
        rels = getrelations(item)
        if rels:
            itemj['relations'] = rels

        models.saveCompetency(itemj)
        # if not db:
        #     with open('./json/%s.json' % getfn(itemj['title']), 'w') as f:
        #         json.dump(itemj, f, indent=4)

    return "done"

def gettitle(item):
    t = item.find('StatementCodes/StatementCode').text
    if t: 
        return t.strip()
    else:
        return None

def getdescription(item):
    return item.find('Statements/Statement').text.strip()

def geturi(item):
    return item.find('RefURI').text.strip()

def getids(item):
    return [geturi(item), item.attrib.get('RefID', ''), gettitle(item)]

def getlevels(item):
    # for l in item.find('GradeLevels'):
    #             print l.text.strip()
    return [s.text.strip() for s in item.find('GradeLevels')]

def getrelations(item):
    rels = {}
    rlsi = item.find('RelatedLearningStandardItems')
    if rlsi is not None:
        for s in rlsi:
            atr = s.attrib['RelationshipType']
            if atr == 'childOf':
                if not rels.get('childof'):
                    rels['childof'] = []
                rels['childof'].append(s.text.strip())
            else:
                print "who weird we got a different relationship type: %s" % atr
    return rels