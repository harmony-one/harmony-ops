import requests
import json
import argparse
import sys

from pyhmy import cli
import pyhmy

num_blockchain = []
num_bad_get_blocks = []

hash_blockchain = []
hash_bad_get_blocks = []


def parse_args():
    parser = argparse.ArgumentParser(description='Funding script for a new network')
    parser.add_argument("endpoint", help="endpoint of blockchain to fetch")
    parser.add_argument("--by-hash", dest="by_hash", action="store_true", help="get blockchain by hashes")
    parser.add_argument("--get_txs", dest="get_txs", action="store_true", help="get tx data for each block")
    return parser.parse_args()


def setup():
    assert hasattr(pyhmy, "__version__")
    assert pyhmy.__version__.major == 20, "wrong pyhmy version"
    assert pyhmy.__version__.minor == 1, "wrong pyhmy version"
    assert pyhmy.__version__.micro >= 14, "wrong pyhmy version, update please"
    env = cli.download("./bin/hmy", replace=False)
    cli.environment.update(env)
    cli.set_binary("./bin/hmy")


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


if __name__ == "__main__":
    args = parse_args()
    setup()
    curr_height = get_curr_block_height(args.endpoint)
    for k, i in enumerate(reversed(range(0, curr_height))):
        sys.stdout.write(f"\rFetched {k}/{curr_height} blocks")
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
    sys.stdout.write(f"\r")
    sys.stdout.flush()
    if not args.by_hash:
        print(f"\nTotal bad loads with number: {len(num_bad_get_blocks)}")
        with open(f'num_blockchain.json', 'w') as f:
            json.dump(num_blockchain, f, indent=4)
        with open(f'num_blockchain-bad-load.json', 'w') as f:
            json.dump(num_bad_get_blocks, f, indent=4)
    else:
        print(f"\nTotal bad loads with hash: {len(hash_bad_get_blocks)}")
        with open(f'hash_blockchain.json', 'w') as f:
            json.dump(hash_blockchain, f, indent=4)
        with open(f'hash_blockchain-bad-load.json', 'w') as f:
            json.dump(hash_bad_get_blocks, f, indent=4)
