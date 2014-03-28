import urllib
import requests
import datetime
import xml.etree.ElementTree as ET
import pytz
import copy
from xci import models

# Medbiq namespaces and types used
mb_namespaces = {'cf': 'http://ns.medbiq.org/competencyframework/v1/',
              'lom': 'http://ltsc.ieee.org/xsd/LOM',
              'pf': "http://ns.medbiq.org/performanceframework/v1/",
              'cobj': "http://ns.medbiq.org/competencyobject/v1/",
              'dcterms': "http://purl.org/dc/terms/",
              'rdf': "http://www.w3.org/1999/02/22-rdf-syntax-ns#"}

MB_COMP_TYPE = 'http://ns.medbiq.org/competencyobject/v1/'
MB_COMP_FWK_TYPE = 'http://ns.medbiq.org/competencyframework/v1/'
MB_PER_FWK_TYPE = 'http://ns.medbiq.org/performanceframework/v1/'

# Returns if it is a Medbiq doc
def isMB(comp_json):
    return (comp_json.get('type', '') == MB_COMP_TYPE) or \
           (comp_json.get('type', '') == MB_COMP_FWK_TYPE) or \
           (comp_json.get('type', '') == MB_PER_FWK_TYPE)

# Return xml from given uri
def getXML(uri):
    res = requests.get(addXMLSuffix(copy.copy(uri))).text
    return ET.XML(res, parser=ET.XMLParser(encoding='utf-8'))

def parseComp(uri):
    types = {'{http://ns.medbiq.org/competencyframework/v1/}CompetencyFramework' : 
                {'parser': parseMedBiqCompXML, 'getmodel': models.getCompetencyFramework},
            '{http://ns.medbiq.org/competencyobject/v1/}CompetencyObject' : 
                {'parser': parseMedBiqCompXML, 'getmodel': models.getCompetency},
            '{http://ns.medbiq.org/performanceframework/v1/}PerformanceFramework' : 
                {'parser': parseMedBiqPerfXML, 'getmodel': models.getPerformanceFramework} }
    # url = uri
    # res = requests.get(addXMLSuffix(copy.copy(uri))).text
    # xmlbit = ET.fromstring(res)
    # xmlbit = ET.XML(res, parser=ET.XMLParser(encoding='utf-8'))
    xmlbit = getXML(uri)
    existing = types[xmlbit.tag]['getmodel'](uri)
    if existing:
        existing.pop('_id', False)
        return existing
    return types[xmlbit.tag]['parser'](xmlbit)


def parseMedBiqCompXML(xmlbit, parentURI=None):
    obj = {}
    obj['type'] = MB_COMP_FWK_TYPE if 'CompetencyFramework' in xmlbit.tag else MB_COMP_TYPE
    obj['uri'] = getEntry(xmlbit)
    obj['ids'] = [obj['uri']]
    obj['title'] = getTitle(xmlbit)
    obj['description'] = getDescription(xmlbit)
    obj['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
    obj = addParent(obj, parentURI)
    for include in xmlbit.findall('cf:Includes', namespaces=mb_namespaces):
        if not obj.get('competencies', False):
            obj['competencies'] = []
        # url = addXMLSuffix(include.find('cf:Entry', namespaces=mb_namespaces).text.strip())
        # nxt = ET.fromstring(requests.get(url).text)
        # nxt = ET.XML(requests.get(url).text, parser=ET.XMLParser(encoding='utf-8'))
        uri = include.find('cf:Entry', namespaces=mb_namespaces).text.strip()
        c = models.getCompetency(uri)
        if not c:
            c = models.getCompetencyFramework(uri)
        if not c:
            nxt = getXML(uri)
            c = parseMedBiqCompXML(nxt, obj['uri'])
        obj['competencies'].append(c)
        obj = addChild(obj, c['uri'])
    # removed this for now... look at medbiq compfwk Relation later: return structure(xmlbit, obj)
    ### save this object to the db, whatever it is
    if obj['type'] == MB_COMP_TYPE:
        models.saveCompetency(obj)
    else:
        models.saveCompetencyFramework(obj)
    # obj.pop('_id', False)
    return obj

def addParent(obj, parentURI):
    if parentURI:
        if not obj.get('relations', False):
            obj['relations'] = {}
        if not obj['relations'].get('childof'):
            obj['relations']['childof'] = []
        obj['relations']['childof'].append(parentURI)
    return obj

def addChild(obj, childURI):
    if childURI:
        if not obj.get('relations', False):
            obj['relations'] = {}
        if not obj['relations'].get('parentof'):
            obj['relations']['parentof'] = []
        obj['relations']['parentof'].append(childURI)
    return obj

def parseMedBiqPerfXML(xmlbit):
    obj = {}
    obj['type'] = MB_PER_FWK_TYPE
    obj['uri'] = getEntry(xmlbit)
    obj['ids'] = [obj['uri']]
    obj['title'] = getTitle(xmlbit)
    obj['description'] = getDescription(xmlbit)
    obj['lastmodified'] = datetime.datetime.now(pytz.utc).isoformat()
    obj['linked_content'] = getReferences(xmlbit)
    obj['components'] = getComponents(xmlbit)
    models.savePerformanceFramework(obj)
    # obj.pop('_id', False)
    return obj

def getReferences(xmlbit):
    refs = []
    for ref in xmlbit.findall('pf:SupportingInformation/pf:Reference', namespaces=mb_namespaces):
        r = {}
        r['objectid'] = ref.find('rdf:Description', namespaces=mb_namespaces).attrib.values()[0].strip()
        typexml = ref.find('rdf:Type', namespaces=mb_namespaces)
        if typexml is not None:
            r['type'] = typexml.attrib.values()[0].strip()
        r['contenttype'] = ref.find('dcterms:format', namespaces=mb_namespaces).text.strip()
        refs.append(r)
    return refs

def getComponents(xmlbit):
    obj = []
    for compo in xmlbit.findall('pf:Component', namespaces=mb_namespaces):
        c = {}
        c['id'] = compo.attrib.values()[0].strip()
        c['title'] = compo.find('pf:Title', namespaces=mb_namespaces).text.strip()
        for comp in compo.findall('pf:Competency/pf:Reference', namespaces=mb_namespaces):
            if not c.get('competencies'):
                c['competencies'] = []
            co = {}
            co['entry'] = comp.find('rdf:Description', namespaces=mb_namespaces).attrib.values()[0].strip()
            co['type'] = comp.find('rdf:Type', namespaces=mb_namespaces).attrib.values()[0].strip()
            parseComp(co['entry'])
            c['competencies'].append(co)
        for pl in compo.findall('pf:PerformanceLevelSet/pf:PerformanceLevel', namespaces=mb_namespaces):
            if not c.get('performancelevels'):
                c['performancelevels'] = []
            perlvl = {}
            perlvl['displayorder'] = pl.find('pf:DisplayOrder', namespaces=mb_namespaces).text.strip()
            perlvl['score'] = {'singlevalue': pl.find('pf:Score/pf:SingleValue', namespaces=mb_namespaces).text.strip()}
            perlvl['id'] = pl.find('pf:Indicator', namespaces=mb_namespaces).attrib.values()[0].strip()
            perlvl['description'] = pl.find('pf:Indicator/pf:Description', namespaces=mb_namespaces).text.strip()
            c['performancelevels'].append(perlvl)
        obj.append(c)
    return obj

def getEntry(xml):
    return xml.find('lom:lom/lom:general/lom:identifier/lom:entry', namespaces=mb_namespaces).text.strip()

def getTitle(xml):
    return xml.find('lom:lom/lom:general/lom:title/lom:string[@language="en"]', namespaces=mb_namespaces).text.strip()

def getDescription(xml):
    return xml.find('lom:lom/lom:general/lom:description/lom:string[@language="en"]', namespaces=mb_namespaces).text.strip()

def addXMLSuffix(url):
    if url.endswith('.xml'):
        return url
    return url + ".xml"
