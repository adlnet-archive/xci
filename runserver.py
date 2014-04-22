from xci import config_app
from pymongo import MongoClient


# Run the app
app = config_app('prod')
# app.run(debug=True)