#bin/python3

import argparse
import common
import threading
import http.server
import socketserver
import os, sys
import time
import queue
from collect_data import collect_data
from datetime import datetime
from jinja2 import Environment, FileSystemLoader
import pandas as pd

data = pd.DataFrame()

def monitor(address_list, round, data, out):
    print("Starting monitor")
    df = collect_data(address_list, round)

    if data.empty:
        data = df
    else:
        data = data.append(df)

    latest_data = data.loc[data["index"] == round]
    prev_data = data.loc[data["index"] == (round - 4)]

    calculated = {}
    if not prev_data.empty:
        for index, value in latest_data.iterrows():
            shard, address = value["shard"], value["address"]
            if shard not in list(calculated.keys()):
                calculated[shard] = {}
            address = value["address"]
            past_value = prev_data.loc[prev_data["address"] == address].iloc[0]
            calculated[shard][address] = f'{value["balance"] - past_value["balance"]:.4f}'

        for k in calculated.keys():
            calculated[k] = {key: value for key, value in sorted(calculated[k].items(), key = lambda item: item[1], reverse = True)}
    else:
        for index, value in latest_data.iterrows():
            shard, address = value["shard"], value["address"]
            if shard not in list(calculated.keys()):
                calculated[shard] = {}
            calculated[shard][address] = "NA"

    env = Environment(loader = FileSystemLoader('templates/'), auto_reload = False)
    template = env.get_template('base.html.j2')
    with open('index.html', 'w') as f:
        f.write(template.render(shards = calculated, time = datetime.now))

    print("Outputted template")
    data = data.loc[data["index"] > round - 10]
    out.put(data)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--address-list', dest = 'address_list', required = True, help = "List of ONE addresses to track")
    parser.add_argument('--verbose', action = 'store_true', help = "Verbose for debug")

    args = parser.parse_args()

    if args.verbose:
        def v_print(s):
            print(s)
    else:
        def v_print(s):
            return

    if not os.path.exists(args.address_list):
        print("Error: File does not exist %s", args.address_list)
        sys.exit(-1)

    addr = common.read_addresses(args.address_list)
    if len(addr) <= 0:
        print("Error: Address list is empty")
        sys.exit(-1)

    round = 0
    q = queue.Queue()
    try:
        while True:
            v_print(datetime.now())
            thread = threading.Thread(target = monitor, args = (addr, round, data, q))
            thread.start()
            round += 1
            time.sleep(900)
            thread.join()
            data = q.get()
            print(data)
    except KeyboardInterrupt:
        pass
