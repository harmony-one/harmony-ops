import argparse
import json
import requests
from flask import render_template
from status import app
from collections import namedtuple

NetworkInfo = namedtuple('NetworkInfo', ['name', 'watchdog', 'explorer', 'staking', 'endpoint'])

watchdog = 'http://watchdog.hmny.io/status-%s'
endpoint = 'https://api.s%s.%s.hmny.io'

@app.route('/status')
def status():

    with open('networks.txt', 'r') as f:
        network_list = [NetworkInfo(*[y.strip() for y in x.strip().split(',')]) for x in f if not x[0] == '#']

    statuses = {}
    for n in network_list:
        statuses[n.name] = {}
        statuses[n.name]['block'] = {}
        try:
            r = requests.get(watchdog % n.watchdog, auth=('harmony', 'harmony.one'))
        except requests.exceptions.ConnectionError:
            r = None
        if r is not None:
            result = r.json()
            try:
                for item in result['shard-status']:
                    statuses[n.name]['block'][item['shard-id']] = item
                    e = endpoint % (item['shard-id'], n.endpoint)
                    statuses[n.name]['block'][item['shard-id']]['endpoint'] = e
                    try:
                        s = requests.get(e)
                        statuses[n.name]['block'][item['shard-id']]['endpoint-status'] = True
                    except requests.exceptions.ConnectionError:
                        statuses[n.name]['block'][item['shard-id']]['endpoint-status'] = False
            except json.decoder.JSONDecodeError:
                pass
            #statuses[n.name]['used-seats'] = result['used-seats']
            #statuses[n.name]['avail-seats'] = result['avail-seats']
            statuses[n.name]['commit-version'] = result['commit-version']
            statuses[n.name]['explorer-link'] = n.explorer
            statuses[n.name]['staking-link'] = n.staking

    # Sort output by ShardID
    for net in statuses.keys():
        for k in statuses[net]['block']:
            statuses[net]['block'] = {key: value for key, value in sorted(statuses[net]['block'].items(), key = lambda item: item[1]['shard-id'])}

    return render_template('status.html.j2', data = statuses)
