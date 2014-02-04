from xci import app, competency
from flask import make_response, request
import json

@app.route('/')
def index():
    uri = request.args.get('uri', None)
    if uri:
        p = competency.parseMedBiq(uri)
        try:
            resp = make_response(json.dumps(p), 200)
            resp.headers['Content-Type'] = "application/json"
            return resp
        except Exception as e:
            return make_response("%s<br>%s" % (str(e), p), 200)
            # return make_response("fail <br> %s" % repr(p), 200)

    return '''yay we dids it! 
              <br>DEBUG: %s 
              <br>SECRET: %s
              <br><a href="./?uri=http://adlnet.gov/competency-framework/scorm/choosing-an-lms.xml">choose lms</a>
              <br><a href="./?uri=http://adlnet.gov/competency-framework/computer-science/basic-programming.xml">programming</a>
              <br><a href="./?uri=http://12.109.40.34/performance-framework/xapi/tetris.xml">perf tetris</a>''' % (app.config['DEBUG'], app.config['SECRET_KEY'])