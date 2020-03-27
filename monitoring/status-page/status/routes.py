import argparse
import json
import queue
import requests
from collections import namedtuple
from flask import render_template
from status import app
from threading import Thread

NetworkInfo = namedtuple('NetworkInfo', ['watchdog', 'explorer', 'staking', 'endpoint'])

watchdog = 'http://watchdog.hmny.io/status-%s'
endpoint = 'https://api.s%s.%s.hmny.io'

statuses = {}
watchdog_queue = queue.Queue(maxsize = 0)
endpoint_queue = queue.Queue(maxsize = 0)

@app.route('/status')
def status():

    with open('networks.txt', 'r') as f:
        network_list = {x.strip().split(',')[0].strip(): NetworkInfo(*[y.strip() for y in x.strip().split(',')][1:]) for x in f if not x[0] == '#'}

    watchdog_threads = []
    for n in network_list.keys():
        statuses[n] = {}
        statuses[n]['block'] = {}
        statuses[n]['explorer-link'] = network_list[n].explorer
        statuses[n]['staking-link'] = network_list[n].staking
        watchdog_threads.append(Thread(target = query_watchdog, args = (n, network_list[n].watchdog, watchdog_queue)))

    for w in watchdog_threads:
        w.start()

    for w in watchdog_threads:
        w.join()

    endpoint_threads = []
    while not watchdog_queue.empty():
        network_name, result = watchdog_queue.get()
        for item in result['shard-status']:
            id = item['shard-id']
            e = endpoint % (item['shard-id'], network_list[network_name].endpoint)
            statuses[network_name]['block'][id] = item
            statuses[network_name]['block'][id]['endpoint'] = e
            endpoint_threads.append(Thread(target = check_endpoint, args = (e, id, network_name, endpoint_queue)))
        if len(result['commit-version']) == 1:
            statuses[network_name]['commit-version'] = result['commit-version'][0]
        else:
            statuses[network_name]['commit-version'] = ", ".join(sorted(result['commit-version']))
        statuses[network_name]['used-seats'] = result['used-seats']
        statuses[network_name]['avail-seats'] = result['avail-seats']
        statuses[network_name]['validators'] = result['validators']

    for e in endpoint_threads:
        e.start()

    for e in endpoint_threads:
        e.join()

    while not endpoint_queue.empty():
        network_name, shard_id, avail = endpoint_queue.get()
        statuses[network_name]['block'][shard_id]['endpoint-status'] = avail

    # Sort output by ShardID
    for net in statuses.keys():
        for k in statuses[net]['block']:
            statuses[net]['block'] = {key: value for key, value in sorted(statuses[net]['block'].items(), key = lambda item: item[1]['shard-id'])}

    return render_template('status.html.j2', data = statuses)

def query_watchdog(network_name, network_watchdog, q):
    try:
        r = requests.get(watchdog % network_watchdog, auth=('harmony', 'harmony.one'))
    except requests.exceptions.ConnectionError:
        return

    try:
        result = r.json()
        q.put((network_name, result))
    except json.decoder.JSONDecodeError:
        pass

def check_endpoint(endpoint, shard_id, network_name, q):
    try:
        s = requests.get(endpoint)
        avail = True
    except requests.exceptions.ConnectionError:
        avail = False
    q.put((network_name, shard_id, avail))
