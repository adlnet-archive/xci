from flask import Flask

app = Flask(__name__)

def config_app(config_filename=None):
    # This was intended for multiple settings files depending on if you were running for testing, production, etc
    if config_filename:
        app.config.from_pyfile(config_filename)
    else:
        app.config.from_object('xci.settings.dev')

    # Import views and return the app
    import xci.views
    return app