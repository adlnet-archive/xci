from flask import Flask

app = Flask(__name__)

def config_app(config_filename=None):
    if config_filename:
        app.config.from_pyfile(config_filename)
    else:
        app.config.from_object('xci.settings.dev')


    import xci.views

    return app