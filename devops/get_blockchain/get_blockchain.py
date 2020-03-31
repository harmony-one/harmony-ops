#!/usr/bin/env python3
"""
Simple script to get all blocks of a blockchain.

Note that this is currently done sequentially.

The script will create (or replace) the following files:
    1) `blockchain.json`: An ordered (desc) JSON array of all the blocks
    2) `blockchain-bad-load.json`: An ordered (desc) list of block numbers that could not be fetched.

Ex:
    $ python3 get_blockchain.py http://localhost:9500/ --min-height 1000  --max-height 10000 --print | jq
    $ python3 get_blockchain.py http://localhost:9500/ --min-height 1000  --max-height 10000 --stats
    $ python3 get_blockchain.py http://localhost:9500/ --min-height 1000  --max-height 10000 --no-txs --stats
"""
import requests
import json
import argparse
import sys

num_blockchain = []
num_bad_get_blocks = []

hash_blockchain = []
hash_bad_get_blocks = []


def parse_args():
    parser = argparse.ArgumentParser(description='Simple script to get all blocks of a blockchain')
    parser.add_argument("endpoint", help="endpoint of blockchain to fetch")
    parser.add_argument("--max-height", dest="max_height", default=None, type=int, help="set the max block height, "
                                                                                        "default is None.")
    parser.add_argument("--min-height", dest="min_height", default=None, type=int, help="set the min block height, "
                                                                                        "default is None.")
    parser.add_argument("--by-hash", dest="by_hash", action="store_true", help="get blockchain by hashes "
                                                                               "instead of number (not implemented)")
    parser.add_argument("--no-txs", dest="get_txs", action="store_false", help="do NOT get full tx data")
    parser.add_argument("--stats", dest="stats", action="store_true", help="get stats after processing blockchain")
    parser.add_argument("--print", dest="print", action="store_true", help="print blockchain data once done")
    return parser.parse_args()


def get_block_number(block_num, endpoint, get_tx_info=False):
    url = endpoint
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "hmy_getBlockByNumber",
        "params": [
            str(hex(block_num)),
            get_tx_info
        ],
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=30)
    try:
        returned = json.loads(response.content)["result"]
        return returned
    except Exception:  # Catch all to not halt
        num_bad_get_blocks.append({
            'block-num': block_num,
            'reason': f"Failed to json load block {block_num}. Content: {response.content}"
        })
        print(f"\n[!!!] Failed to json load block {block_num}. Content: {response.content}\n")


def get_block_hash(block_hash, endpoint, get_tx_info=False):
    url = endpoint
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "hmy_getBlockByNumber",
        "params": [
            block_hash if block_hash.startswith('0x') else '0x' + block_hash,
            get_tx_info
        ],
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=30)
    try:
        returned = json.loads(response.content)["result"]
        return returned
    except Exception:  # Catch all to not halt
        hash_bad_get_blocks.append({
            'block-hash': block_hash,
            'reason': f"Failed to json load block {block_hash}. Content: {response.content}"
        })
        print(f"\n[!!!] Failed to json load block {block_hash}. Content: {response.content}\n")


def get_latest_header(endpoint):
    url = endpoint
    payload = json.dumps({
        "jsonrpc": "2.0",
        "method": "hmy_latestHeader",
        "params": [
        ],
        "id": 1
    })
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=30)
    return json.loads(response.content)["result"]


def get_curr_block_height(endpoint):
    header = get_latest_header(endpoint)
    return int(header["blockNumber"])


def stats(data):
    print("\n=== Stats for fetched blocks ===\n")
    type_count = {}
    total_tx_count = 0
    staking_tx_count = 0
    plain_tx_count = 0
    plain_tx_amt_count = 0
    print(f"Total Blocks Fetched: {len(data)}")
    for blk in data:
        if 'stakingTransactions' in blk.keys():
            total_tx_count += len(blk['stakingTransactions'])
            for stx in blk['stakingTransactions']:
                staking_tx_count += 1
                if 'type' in stx:
                    if stx['type'] not in type_count:
                        type_count[stx['type']] = 0
                    type_count[stx['type']] += 1
        if 'transactions' in blk.keys():
            total_tx_count += len(blk['transactions'])
            for tx in blk['transactions']:
                plain_tx_count += 1
                if 'value' in tx:
                    atto_amt = int(tx['value'], 16)
                    plain_tx_amt_count += atto_amt * 1e-18
    print(f"Total tx count: {total_tx_count}")
    print(f"Plain tx count: {plain_tx_count}")
    print(f"Total amount sent via plain tx: {plain_tx_amt_count}")
    print(f"Staking tx count: {staking_tx_count}")
    print(f"Staking tx type count breakdown: {json.dumps(type_count, indent=4)}")


if __name__ == "__main__":
    args = parse_args()
    max_height = get_curr_block_height(args.endpoint) if args.max_height is None else args.max_height
    min_height = 0 if args.min_height is None else args.min_height
    assert max_height > min_height
    total_blocks_count = max_height - min_height
    for k, i in enumerate(reversed(range(min_height, max_height))):
        if not args.print:
            sys.stdout.write(f"\rFetched {k}/{total_blocks_count} blocks")
            sys.stdout.flush()
        if not args.by_hash:
            block = get_block_number(i, args.endpoint, args.get_txs)
            if block is None:
                num_bad_get_blocks.append({
                    'block-num': i,
                    'reason': f"Block {i} had a null response: {block}"
                })
                print(f"\n[!] WARNING block {i} had a null response: {block}\n")
            elif block['stakingTransactions'] is None or type(block['stakingTransactions']) != list:
                num_bad_get_blocks.append({
                    'block-num': i,
                    'reason': f"Block {i} had a null response for staking transactions: {block['stakingTransactions']}"
                })
                print(f"\n[!] WARNING Block {i} had a null response for staking transactions: "
                      f"{block['stakingTransactions']}\n")
            elif block['transactions'] is None or type(block['transactions']) != list:
                num_bad_get_blocks.append({
                    'block-num': i,
                    'reason': f"Block {i} had a null response for plain transactions: {block['transactions']}"
                })
                print(f"\n[!] WARNING block {i} had a null response for plain transactions: "
                      f"{block['transactions']}\n")
            num_blockchain.append(block if block else {})
        else:
            raise Exception("Not implemented")
    if not args.print:
        sys.stdout.write(f"\r")
        sys.stdout.flush()
    if not args.by_hash:
        if not args.print:
            print(f"\nTotal bad loads with number: {len(num_bad_get_blocks)}")
        with open(f'blockchain.json', 'w') as f:
            json.dump(num_blockchain, f, indent=4)
        with open(f'blockchain-bad-load.json', 'w') as f:
            json.dump(num_bad_get_blocks, f, indent=4)
        if args.stats:
            stats(num_blockchain)
        if args.print:
            print(json.dumps(num_blockchain))
    else:
        if not args.print:
            print(f"\nTotal bad loads with hash: {len(hash_bad_get_blocks)}")
        with open(f'blockchain.json', 'w') as f:
            json.dump(hash_blockchain, f, indent=4)
        with open(f'blockchain-bad-load.json', 'w') as f:
            json.dump(hash_bad_get_blocks, f, indent=4)
        if args.stats:
            stats(num_blockchain)
        if args.print:
            print(json.dumps(hash_blockchain))
