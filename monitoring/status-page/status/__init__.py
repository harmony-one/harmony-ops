from flask import Flask

app = Flask(__name__)

from status import routes
