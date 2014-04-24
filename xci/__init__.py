from flask import Flask
from werkzeug.contrib.fixers import ProxyFix

app = Flask(__name__)
# app.wsgi_app = ProxyFix(app.wsgi_app)

def config_app(config_filename=None):
    # This was intended for multiple settings files depending on if you were running for testing, production, etc
    if config_filename:
    	config_filename = 'xci.settings.' + config_filename
        app.config.from_object(config_filename)
    else:
        app.config.from_object('xci.settings.dev')

    # Import views and return the app
    import xci.views
    return app