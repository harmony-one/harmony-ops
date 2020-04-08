import json

import requests
import pexpect

default_endpoint = "https://api.s0.os.hmny.io/"


def get_current_epoch(endpoint=default_endpoint):
    return int(get_latest_header(endpoint)["epoch"])


def get_latest_header(endpoint=default_endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_latestHeader",
                          "params": []})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json.loads(response.content)["result"]


def get_latest_headers(endpoint=default_endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_getLatestChainHeaders",
                          "params": []})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json.loads(response.content)["result"]


def get_staking_epoch(endpoint=default_endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_getNodeMetadata",
                          "params": []})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    return int(body["result"]["chain-config"]["staking-epoch"])


def get_validator_information(address, endpoint=default_endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_getValidatorInformation",
                          "params": [address]})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    if 'error' in body:
        raise RuntimeError(str(body['error']))
    return body['result']


def process_passphrase(proc, passphrase, double_take=False):
    """
    This will enter the `passphrase` interactively given the pexpect child program, `proc`.
    """
    proc.expect("Enter passphrase:\r\n")
    proc.sendline(passphrase)
    if double_take:
        proc.expect("Repeat the passphrase:\r\n")
        proc.sendline(passphrase)
        proc.expect("\n")
