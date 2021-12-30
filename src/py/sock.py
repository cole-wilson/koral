import asyncio
import websockets
import pickle
import fnmatch
import json
from base64 import b64encode as btoa, b64decode as atob
import jug
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)
import flask
from flask_cors import CORS, cross_origin

app = flask.Flask(__name__)
cors = CORS(app)
app.config['CORS_HEADERS'] = 'Content-Type'

class Store():
    def __init__(self):
        self.data = {}
    def exists(self, key):
        return key in self.data
    def delete(self, key):
        del self.data[key]
    def getset(self, key, newvalue):
        oldvalue = self.data[key] if key in self.data else None
        self.data[key] = newvalue
        return oldvalue
    def set(self, key, value):
        self.data[key] = value
    def keys(self, pattern):
        return fnmatch.filter(list(self.data.keys()), pattern)

store = Store()
@app.route('/', methods=["GET", "POST"])
@cross_origin()
def main():
    global store
    data = flask.request.get_data().decode()
    data = atob(data)
    data = jug.backends.encode.decode(data)
    name, args = data
    response = getattr(store, name)(*args)
    encoded = jug.backends.encode.encode(response)
    return btoa(encoded)

app.run('0.0.0.0', 8080)
