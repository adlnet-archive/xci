from xci import app

@app.route('/')
def index():
    return 'yay we dids it! <br>DEBIG: %s <br>SECRET: %s' % (app.config['DEBUG'], app.config['SECRET_KEY'])