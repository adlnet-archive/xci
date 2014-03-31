# -*- coding: utf-8 -*-
from lxml import etree

CO_NS = "http://ns.medbiq.org/competencyobject/v1/"
XSI = "http://www.w3.org/2001/XMLSchema-instance"
CO = "{%s}" % CO_NS
NSMAP = {None : CO_NS,
         "lom" : "http://ltsc.ieee.org/xsd/LOM",
         "ex" : "http://ltsc.ieee.org/xsd/LOM/extend",
         "ag" : "http://ltsc.ieee.org/xsd/LOM/unique",
         "voc" : "http://ltsc.ieee.org/xsd/LOM/vocab",
         "a" : "http://ns.medbiq.org/address/v1/",
         "hx" : "http://ns.medbiq.org/lom/extend/v1/",
         "hv" : "http://ns.medbiq.org/lom/vocab/v1/",
         "xsi" : XSI}

# some crazy characters can wreak havok on this system.. these take em out
def is_valid_xml_char_ordinal(i):
    """
    Defines whether char is valid to use in xml document
    XML standard defines a valid char as::
    Char ::= #x9 | #xA | #xD | [#x20-#xD7FF] | [#xE000-#xFFFD] | [#x10000-#x10FFFF]
    """
    return ( # conditions ordered by presumed frequency
            0x20 <= i <= 0xD7FF
            or i in (0x9, 0xA, 0xD)
            or 0xE000 <= i <= 0xFFFD
            or 0x10000 <= i <= 0x10FFFF
            )

def clean_xml_string(s):
    """
    Cleans string from invalid xml chars
    Solution was found there::
    http://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python
    """
    return ''.join(c for c in s if is_valid_xml_char_ordinal(ord(c)))

def __getRoot():
    root = etree.Element(CO + "CompetencyObject", nsmap=NSMAP)
    root.attrib['{{{pre}}}schemaLocation'.format(pre=XSI)] = "http://ns.medbiq.org/competencyobject/v1/ competencyobject.xsd"
    return root

def __getLOMString(parent, s, language="en"):
    lomstring = etree.SubElement(parent, "{%s}" % NSMAP['lom'] + "string")
    lomstring.attrib['language'] = language
    lomstring.text = s
    return lomstring

def __addLevels(parent, s):
    # educational
    # description - langstring
    ed = etree.SubElement(parent, "{%s}" % NSMAP['lom'] + 'educational')
    lvl = etree.SubElement(ed, "{%s}" % NSMAP['lom'] + "description")
    __getLOMString(lvl, s)
    return ed
    
# makes medbiq xml
def toXML(comp_json):
    root = __getRoot()
    lom = etree.SubElement(root, "{%s}" % NSMAP['lom'] + "lom")
    lomgeneral = etree.SubElement(lom, "{%s}" % NSMAP['lom'] + "general")
    lomidentifier = etree.SubElement(lomgeneral, "{%s}" % NSMAP['lom'] + "identifier")
    lomcatalog = etree.SubElement(lomidentifier, "{%s}" % NSMAP['lom'] + "catalog")
    lomcatalog.text = "URI"
    lomentry = etree.SubElement(lomidentifier, "{%s}" % NSMAP['lom'] + "entry")
    lomentry.text = comp_json.get('uri', 'http://example.com/your/uri/here')
    lomtitle = etree.SubElement(lomgeneral, "{%s}" % NSMAP['lom'] + "title")
    titlestr = __getLOMString(lomtitle, clean_xml_string(comp_json.get('title', 'your title here')))
    lomdescr = etree.SubElement(lomgeneral, "{%s}" % NSMAP['lom'] + "description")
    descrstr = __getLOMString(lomdescr, clean_xml_string(comp_json.get('description', 'your description here')))
    if comp_json.get('levels', False):
        __addLevels(lom, clean_xml_string(','.join(comp_json.get('levels', []))))
    return etree.tostring(root, pretty_print=True, encoding="utf-8")

# <CompetencyObject xmlns="http://ns.medbiq.org/competencyobject/v1/" 
#     xmlns:lom="http://ltsc.ieee.org/xsd/LOM" 
#     xmlns:ex="http://ltsc.ieee.org/xsd/LOM/extend" 
#     xmlns:ag="http://ltsc.ieee.org/xsd/LOM/unique" 
#     xmlns:voc="http://ltsc.ieee.org/xsd/LOM/vocab" 
#     xmlns:a="http://ns.medbiq.org/address/v1/" 
#     xmlns:hx="http://ns.medbiq.org/lom/extend/v1/" 
#     xmlns:hv="http://ns.medbiq.org/lom/vocab/v1/" 
#     xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" 
#     xsi:schemaLocation="http://ns.medbiq.org/competencyobject/v1/_object.xsd"> 
#     <lom:lom> 
#         <lom:general> 
#             <lom:identifier> 
#                 <lom:catalog>URI</lom:catalog> 
#                 <lom:entry>http://adlnet.gov/competency/computer-science/understanding-variables</lom:entry> 
#             </lom:identifier> 
#             <lom:title> 
#                 <lom:string language="en">Understanding Variables</lom:string> 
#             </lom:title> 
#             <lom:description> 
#                 <lom:string language="en">Exhibits an understanding of variables and their uses.</lom:string> 
#             </lom:description> 
#         </lom:general>
#     </lom:lom> 
# </CompetencyObject>
