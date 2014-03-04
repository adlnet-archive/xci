import requests
import json
import datetime
import pytz
import xml.etree.ElementTree as ET
from xci import models

CCObjectType = 'commoncoreobject'

def getfn(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    
    return ''.join(c for c in s if c in valid_chars)


def getCommonCore():
    parts = ["http://www.corestandards.org/Math.xml",
             "http://www.corestandards.org/ELA-Literacy.xml"]
    
    # see if common core objects are already in db
    exists = models.findoneComp({'type':'commoncoreobject'})
    if exists:
        return

    for p in parts:
        try:
            res = requests.get(p).text
        except Exception, e:
            print e
            return None
        
        try:
            saveCCXMLinDB(ET.XML(res, parser=ET.XMLParser(encoding='utf-8')))
            # saveCCXMLinDB(ET.fromstring(res))
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
        itemj['description'] = getdescription(item)
        itemj['uri'] = geturi(item)
        itemj['ids'] = getids(item)
        itemj['type'] = CCObjectType
        itemj['levels'] = getlevels(item)
        itemj['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
        rels = getrelations(item)
        if rels:
            itemj['relations'] = rels

        models.saveCompetency(itemj)


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
                print "we got an unexpected relationship type: %s" % atr
    return rels
