import argparse
import json
import requests
from collections import namedtuple
from flask import render_template
from multiprocessing.pool import Pool
from status import app
from threading import Lock

NetworkInfo = namedtuple('NetworkInfo', ['name', 'watchdog', 'explorer', 'staking', 'endpoint'])

watchdog = 'http://watchdog.hmny.io/status-%s'
endpoint = 'https://api.s%s.%s.hmny.io'

statuses = {}
pool = Pool()
threads = []
lock = Lock()

@app.route('/status')
def status():

    with open('networks.txt', 'r') as f:
        network_list = [NetworkInfo(*[y.strip() for y in x.strip().split(',')]) for x in f if not x[0] == '#']

    for n in network_list:
        lock.acquire()
        statuses[n.name] = {}
        statuses[n.name]['block'] = {}
        statuses[n.name]['explorer-link'] = n.explorer
        statuses[n.name]['staking-link'] = n.staking
        lock.release()
        query_watchdog(n.name, n.watchdog, n.endpoint)
        #threads.append(pool.apply_async(query_watchdog, (n.name, n.watchdog, n.endpoint)))

    for t in threads:
        t.get()

    pool.close()

    # Sort output by ShardID
    for net in statuses.keys():
        for k in statuses[net]['block']:
            statuses[net]['block'] = {key: value for key, value in sorted(statuses[net]['block'].items(), key = lambda item: item[1]['shard-id'])}

    return render_template('status.html.j2', data = statuses)

def query_watchdog(network_name, network_watchdog, network_endpoint):
    try:
        r = requests.get(watchdog % network_watchdog, auth=('harmony', 'harmony.one'))
    except requests.exceptions.ConnectionError:
        return

    try:
        result = r.json()
        for i in result['shard-status']:
            id = item['shard-id']
            e = endpoint % (item['shard-id'], network_endpoint)
            lock.acquire()
            statuses[network_name]['block'][id] = item
            statuses[network_name]['block'][id]['endpoint'] = e
            lock.release()
            #threads.append(pool.apply_async(check_endpoint, (e, id, network_name)))
            check_endpoint(e, id, network_name)
        lock.acquire()
        statuses[network_name]['commit-version'] = result['commit-version']
        statuses[network_name]['used-seats'] = result['used-seats']
        statuses[network_name]['avail-seats'] = result['avail-seats']
        lock.release()
    except json.decoder.JSONDecodeError:
        pass

def check_endpoint(endpoint, shard_id, network_name):
    try:
        s = requests.get(endpoint)
        avail = True
    except requests.exceptions.ConnectionError:
        avail = False
    lock.acquire()
    statuses[network_name]['block'][shard_id]['endpoint-status'] = avail
    lock.release()
