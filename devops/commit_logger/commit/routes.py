import json
from os import path
from commit import app

base = path.dirname(path.realpath(__file__))
data = path.abspath(path.join(base, 'data'))
json_log = path.join(data, 'commit.json')

@app.route('/commit_log')
def commit_log():
    if path.exists(json_log):
        with open(json_log, 'r') as f:
            out = ''.join([x.strip() for x in f])
        return out
    return '{"error":"missing data file"}'
