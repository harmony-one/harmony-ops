from flask import Flask

app = Flask(__name__)

from commit import routes
