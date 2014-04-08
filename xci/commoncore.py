import requests
import json
import datetime
import pytz
import xml.etree.ElementTree as ET
from xml.etree.ElementTree import ParseError
from xci import models
from os import path

CCObjectType = 'commoncoreobject'

def getfn(s):
    import string
    valid_chars = "-_.() %s%s" % (string.ascii_letters, string.digits)
    
    return ''.join(c for c in s if c in valid_chars)

# common core is practically impossible to traverse. they essentially made a 
# flat structure. instead of dealing with this nightmare, i just pull in everything.
# at one time, they were at the urls listed in 'parts'. they since took the xml versions 
# away. i leave them here in hopes that they will bring them back.
# inspite of this, the system will try to read from file, assuming the xml is at the paths 
# seen below at the ET.parse lines.
def getCommonCore():
    parts = ["http://www.corestandards.org/Math.xml",
             "http://www.corestandards.org/ELA-Literacy.xml"]
    
    # see if common core objects are already in db
    # if one is there all should be there
    exists = models.findoneComp({'type':'commoncoreobject'})
    if exists:
        return

    for p in parts:
        # internet attempt
        try:
            res = requests.get(p).text
        except Exception, e:
            print e
            res = ""

        # try to parse internet result
        try:
            thexml = ET.XML(res, parser=ET.XMLParser(encoding='utf-8'))
        except ParseError:
            try: 
                # parse failed try getting file version
                # i'm looping so just figure out which of the 2 parts i'm on
                if p == parts[0]:
                    thexml = ET.parse(path.abspath('../ccssi/xml/math.xml'))
                else:
                    thexml = ET.parse(path.abspath('../ccssi/xml/ela-literacy.xml'))
            except Exception, e:
                print e
                # if that didn't work, give up
                return None
        
        try:
            saveCCXMLinDB(thexml)
        except Exception, e:
            print e
            return None

# loop through all items and save data to db
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
