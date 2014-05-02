import base64

DEBUG = True
SECRET_KEY = 'd\xfd\x82\xc6\x88\x8e\x95k>\xa2\xe0GKN\xe3\xe5^\x99\xa9\n\xf4\x88o4'
DOMAIN_NAME = 'http://localhost:5000'

DEFAULT_PROFILE = {
    "name" : "Default LRS Profile",
    "endpoint" : "http://localhost:8000/xapi/",
    # "endpoint" : "https://lrs.adlnet.gov/xapi/",
    "auth" : "Basic %s" % base64.b64encode("%s:%s" % ("tom", "1234")),
    "username" : "tom",
    "password" : "1234"
}

ALLOWED_BADGE_EXTENSIONS = set(['png'])
BADGE_UPLOAD_FOLDER = 'static/badgeclass'

LR_PUBLISH_NAME = "lou.wolford.ctr@adlnet.gov"
LR_PUBLISH_PASSWORD = "$c0rmR0ck$"
LR_PUBLISH_ENDPOINT = "https://sandbox.learningregistry.org/publish"

# lr uri to obtain docs
LR_NODE = "http://node01.public.learningregistry.net/obtain?request_ID="

HEADERS = {        
    'Authorization': DEFAULT_PROFILE['auth'],
    'content-type': 'application/json',        
    'X-Experience-API-Version': '1.0.0'
}