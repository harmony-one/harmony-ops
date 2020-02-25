import argparse
import json
import requests
from flask import render_template
from status import app

watchdog = 'http://watchdog.hmny.io/status-%s'
network_list = [('Mainnet', 'mainnet'),('LRTN', 'testnet'), ('OSTN', 'staking')]

@app.route('/status')
def status():
    statuses = {}
    for n in network_list:
        r = requests.get(watchdog % n[1], auth=('harmony', 'harmony.one'))
        statuses[n[0]] = {}
        for result in r.json():
            statuses[n[0]][result["shard-id"]] = result

    for net in statuses.keys():
        for k in statuses[net]:
            statuses[net] = {key: value for key, value in sorted(statuses[net].items(), key = lambda item: item[1]["shard-id"])}

    return render_template('status.html.j2', data = statuses)
