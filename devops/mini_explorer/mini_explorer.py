#!/usr/bin/env python3

# Run command:
# python3 -u mini_explorer.py [params] 2&>1 | tee out.log

import argparse
import json, os, sys
import requests
import time
from collections import defaultdict

def latestBlock() -> dict:
    return {"id": "1", "jsonrpc": "2.0",
            "method": "hmy_latestHeader",
            "params": ["latest"]}

def blockByHash(hash) -> dict:
    return {"id": "1", "jsonrpc": "2.0",
            "method": "hmy_getBlockByHash",
            "params": [hash, True]}

def request(endpoint, request, output = False) -> str:
    # Send request
    r = requests.get(endpoint, headers = {'Content-Type':'application/json; charset=utf8'}, data = request)
    # Check for invalid status code
    if r.status_code != 200:
        print("Error: Return status code %s" % r.status_code)
        return None

    # Check for valid JSON format return
    try:
        r.json()
    except ValueError:
        print("Error: Unable to read JSON reply")
        return None

    return r.json()

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--shards', default = 2, type = int, help = 'Number of shards')
    parser.add_argument('--endpoints', required = True, help = 'Endpoints to query from, sorted by shard & seperated by commas')
    parser.add_argument('--sleep', default = 8, type = int, help = 'Sleep timer')

    args = parser.parse_args()

    endpoint = [x.strip() for x in args.endpoints.strip().split(',')]

    if args.shards != len(endpoint):
        print("Number of shards must be equal the number of provided endpoints.")
        sys.exit(-1)

    try:
        while True:
            for x in range(args.shards):
                result = request(endpoint[x], json.dumps(latestBlock()))
                if result != None:
                    hash = result["result"]["blockHash"]
                    next = request(endpoint[x], json.dumps(blockByHash(hash)))
                    if next != None:
                        sx = defaultdict(int)
                        sx["total"] = len(next["result"]["stakingTransactions"])
                        for t in next["result"]["stakingTransactions"]:
                            sx[t["type"]] += 1
                        t = json.dumps({"shard": x,
                                        "leader": result["result"]["leader"],
                                        "timestamp": result["result"]["timestamp"],
                                        "block": result["result"]["blockNumber"],
                                        "epoch": result["result"]["epoch"],
                                        "gas": int(next["result"]["gasUsed"], 0),
                                        "maxGas": int(next["result"]["gasLimit"], 0),
                                        "size": int(next["result"]["size"], 0),
                                        "transactions": len(next["result"]["transactions"]),
                                        "staking": sx})
                        print(t)
            time.sleep(args.sleep)
    except KeyboardInterrupt:
        pass
