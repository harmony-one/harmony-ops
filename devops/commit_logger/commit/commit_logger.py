#!/usr/bin/env python3

import argparse
import json, os
import requests
import time
import logging
import queue
from datetime import datetime
from collections import defaultdict
from os import path
from threading import Thread

base = path.dirname(path.realpath(__file__))
data = path.abspath(path.join(base, 'data'))
json_log = path.join(data, 'commit.json')
backup_log = path.join(data, 'commit.json.bk')
file_time_fmt = '%m%d_%H%I%S'
read_time_fmt = '%m/%d_%H:%I:%S'
headers = {'Content-Type': 'application/json'}

def latestBlock() -> dict:
    return {"id": "1", "jsonrpc": "2.0",
            "method": "hmy_latestHeader",
            "params": ["latest"]}

def nodeMetadata() -> dict:
    return {"id": "1", "jsonrpc": "2.0",
            "method": "hmy_getNodeMetadata",
            "params": []}

def request(endpoint, request, output = False) -> str:
    # Send request
    try:
        r = requests.request('POST', endpoint, headers = headers, data = json.dumps(request), timeout = 5)
    except:
        return None
    if r.status_code != 200:
        return None
    return json.loads(r.content)['result']

if __name__ == '__main__':
    formatted_time = datetime.now().strftime(file_time_fmt)

    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoints', help = 'Endpoints to query from, sorted by shard & seperated by commas')
    parser.add_argument('--output_file', default = path.join(base, 'commit_%s.log' % formatted_time), help = 'File to output log to')
    parser.add_argument('--sleep', default = 60, type = int, help = 'Sleep timer')

    args = parser.parse_args()

    endpoint = []
    if args.endpoints:
        endpoint = [x.strip() for x in args.endpoints.strip().split(',')]

    if not path.exists(data):
        try:
            os.mkdir(data)
        except:
            print("Could not make directory data")
            exit(1)

    # Set up logger
    logger = logging.getLogger("commit_logger")
    logger.setLevel(logging.INFO)
    file_handler = logging.FileHandler(args.output_file)
    file_handler.setLevel(logging.INFO)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    commit_data = defaultdict(lambda: defaultdict(int))

    # If log already exists, read existing data
    if path.exists(json_log):
        with open(json_log, 'r') as f:
            json_string = ''.join([x.strip() for x in f])
        existing_data = json.loads(json_string)
        for key in existing_data.keys():
            for shard in existing_data[key].keys():
                commit_data[key][shard] = existing_data[key][shard]

    def collect_data(shard, q):
        metadata = request(endpoint[shard], nodeMetadata())
        block = request(endpoint[shard], latestBlock())

        if metadata != None and block != None:
            commit = metadata['version']
            height = int(block['blockNumber'])
            logger.info('Commit: %s\tShard: %d\tBlock: %d' % (commit, shard, height))
            q.put((commit, shard, height))

    backup_counter = 0
    while True:
        try:
            if backup_counter > 10:
                logger.info("Creating backup log")
                with open(backup_log, 'w') as f:
                    json.dump(commit_data, f, sort_keys = True, indent = 4)
                backup_counter = 0
            else:
                backup_counter += 1
            threads = []
            q = queue.Queue(maxsize = 0)
            for x in range(len(endpoint)):
                threads.append(Thread(target = collect_data, args = (x, q)))
            for t in threads:
                t.start()
            for t in threads:
                t.join()
            while not q.empty():
                now = datetime.now().strftime(read_time_fmt)
                v, s, h = q.get()
                if not commit_data[v]:
                    commit_data[v]['first'] = now
                if h > commit_data[v][str(s)]:
                    commit_data[v][str(s)] = h
                    commit_data[v]['latest'] = now
            with open(json_log, 'w') as f:
                json.dump(commit_data, f, sort_keys = True, indent = 4)
            time.sleep(args.sleep)
        except Exception as e:
            logger.error("ERROR: %s" % e)
            pass
