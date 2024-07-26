import requests
import json
import sys
import re
import os
from web3 import Web3
from pyhmy import account, blockchain, transaction
from pyhmy.util import convert_hex_to_one
from eth_abi import decode

# Define constants
HARMONY_RPC_URL = "https://a.api.s0.t.hmny.io"
staking_contract = "one1qqqqqqqqqqqqqqqqqqqqqqqqqqqqqq8uuuycsy"
FOURBYTE_API_URL = "https://www.4byte.directory/api/v1/signatures/"


def atto_to_one(atto_amount):
    ONE = 10**18
    return atto_amount / ONE

# Function to get function signature info from 4byte.directory
def get_signature_info(signature):
    response = requests.get(f"{FOURBYTE_API_URL}?hex_signature={signature}")
    response_json = response.json()
    if response_json['count'] > 0:
        return response_json['results'][0]
    return None

# Function to parse the calldata
def parse_calldata(signature_info, data):
    if not signature_info or 'text_signature' not in signature_info:
        return None
    try:
        # Get the types of the parameters from the text signature
        types = re.findall(r'\((.*?)\)', signature_info['text_signature'])[0].split(',')
        decoded_parameters = decode(types, bytes.fromhex(data[10:]))
        return decoded_parameters
    except Exception as err:
        print(f"Error decoding parameters: {err}")
        return None

# Function to get staking transaction history using pyhmy
def get_staking_transaction_history(address):
    transactions = []
    page = 0
    while True:
        response = account.get_staking_transaction_history(
            address,
            page=page,
            include_full_tx=True,
            endpoint=HARMONY_RPC_URL,
            timeout = 120
        )
        if not response:
            break
        transactions.extend(response)
        page += 1
    return transactions

# Function to get normal transaction history using pyhmy
def get_transaction_history(address):
    transactions = []
    page = 0
    while True:
        response = account.get_transaction_history(
            address,
            page=page,
            include_full_tx=True,
            endpoint=HARMONY_RPC_URL,
            timeout = 120
        )
        if not response:
            break
        transactions.extend(response)
        page += 1
    return transactions

def get_epoch_from_block(blocknum):
    block = blockchain.get_block_by_number(block_num=blocknum,
        full_tx=False, include_tx=False,
        include_staking_tx=False, endpoint=HARMONY_RPC_URL)
    return block.get('epoch', 0)

def get_tx_hash_receipt_status(tx_hash):
    tx_receipt = transaction.get_transaction_receipt(tx_hash, HARMONY_RPC_URL)
    return tx_receipt.get('status', 0)

# Main function to gather all staking transactions
def gather_staking_transactions(address):
    # file where the previous staking-tx were processed
    filepath = f"staking-txs/{address}.json"

    # load previous file if any is existing
    if os.path.exists(filepath):
        with open(filepath, 'r') as file:
            staking_txs = json.load(file)
            print(f"Loaded and returned data from {filepath}")
            return staking_txs

    staking_transactions = get_staking_transaction_history(address)
    normal_transactions = get_transaction_history(address)

    all_transactions = []

    for tx in staking_transactions:
        msg=tx['msg']
        epoch = get_epoch_from_block(tx['blockNumber'])
        status = get_tx_hash_receipt_status(tx['hash'])
        all_transactions.append({
            'amount': atto_to_one(msg.get('amount', 0)),
            'delegator_add': msg.get('delegatorAddress', None),
            'validator_add': msg.get('validatorAddress', None),
            'type': tx['type'],
            'blocknumber': tx['blockNumber'],
            'timestamp': tx['timestamp'],
            'epoch': epoch,
            'status': status
        })

    for tx in normal_transactions:
        if tx['to'] == staking_contract:
            signature = tx['input'][:10]
            signature_info = get_signature_info(signature)
            type = signature_info['text_signature'].split('(')[0]

            if signature_info:
                decoded_parameters = parse_calldata(signature_info, tx['input'])
                #print(decoded_parameters)

                if type == "CollectRewards":
                    amount = 0
                    delegator_add = tx['from']
                    validator_add = None
                else:
                    amount = atto_to_one(decoded_parameters[2])
                    delegator_add = convert_hex_to_one(decoded_parameters[0][2:])
                    validator_add = convert_hex_to_one(decoded_parameters[1][2:])

                if decoded_parameters:
                    epoch = get_epoch_from_block(tx['blockNumber'])
                    status = get_tx_hash_receipt_status(tx['hash'])
                    all_transactions.append({
                        'amount': amount,
                        'delegator_add': delegator_add,
                        'validator_add': validator_add,
                        'type': signature_info['text_signature'].split('(')[0],
                        'blocknumber': tx['blockNumber'],
                        'timestamp': tx['timestamp'],
                        'epoch': epoch,
                        'status': status
                    })

    # Sort transactions by timestamp
    all_transactions = sorted(all_transactions, key=lambda x: x['timestamp'])

    write_json_to_file(all_transactions, f"staking-txs/{address}.json")

    return all_transactions

def write_json_to_file(json_object, filename):
    with open(filename, 'w') as file:
        json.dump(json_object, file, indent=4)

    print(f"{filename} has been created")

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Fetch staking transactions for a Harmony address.")
    parser.add_argument("address", type=str, help="Harmony address to fetch staking transactions for.")
    args = parser.parse_args()

    address = args.address
    transactions = gather_staking_transactions(address)

    # Print or save the transactions as needed
    print(json.dumps(transactions, indent=2))