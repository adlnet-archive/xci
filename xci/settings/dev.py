import base64

DEBUG = True
SECRET_KEY = 'd\xfd\x82\xc6\x88\x8e\x95k>\xa2\xe0GKN\xe3\xe5^\x99\xa9\n\xf4\x88o4'

DEFAULT_PROFILE = {
    "name" : "Default LRS Profile",
    "endpoint" : "http://localhost:8000/xapi/",
    # "endpoint" : "https://lrs.adlnet.gov/xapi/",
    "auth" : "Basic %s" % base64.b64encode("%s:%s" % ("tom", "1234")),
    "username" : "tom",
    "password" : "1234"
}

HEADERS = {        
    'Authorization': DEFAULT_PROFILE['auth'],
    'content-type': 'application/json',        
    'X-Experience-API-Version': '1.0.0'
}