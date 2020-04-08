import json
import datetime
import re
import os
import inspect
import traceback

import requests
import pyhmy
from pyhmy import util
from pyhmy import cli
from pyhmy.util import (
    json_load,
    Typgpy
)

ACC_NAMES_ADDED = []
ACC_NAME_PREFIX = "_Test_key_"


def setup_pyhmy():
    # TODO: have stable version of CLI if we are using this in test automation.
    assert hasattr(pyhmy, "__version__")
    assert pyhmy.__version__.major == 20, "wrong pyhmy version"
    assert pyhmy.__version__.minor == 1, "wrong pyhmy version"
    assert pyhmy.__version__.micro >= 27, "wrong pyhmy version, update please"
    env = cli.download("./bin/hmy", replace=False)
    cli.environment.update(env)
    cli.set_binary("./bin/hmy")


def get_sharding_structure(endpoint):
    """
    :param endpoint: An endpoint of a SHARD
    :return: The shading structure of the network associated with the ENDPOINT.
    """
    payload = """{
           "jsonrpc": "2.0",
           "method": "hmy_getShardingStructure",
           "params": [  ],
           "id": 1
       }"""
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json.loads(response.content)


def get_endpoint(shard_number, endpoint):
    """
    :param shard_number: The shard number of the desired endpoint
    :param endpoint: Any endpoint of a network
    """
    structure = get_sharding_structure(endpoint)
    assert shard_number < len(structure["result"])
    return structure["result"][shard_number]["http"]


def get_current_epoch(endpoint):
    """
    :param endpoint: The endpoint of the SHARD to check
    :return: The current epoch of the ENDPOINT
    """
    payload = """{
            "jsonrpc": "2.0",
            "method": "hmy_latestHeader",
            "params": [  ],
            "id": 1
        }"""
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    return int(body["result"]["epoch"])


def get_staking_epoch(endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_getNodeMetadata",
                          "params": []})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    return int(body["result"]["chain-config"]["staking-epoch"])


def is_active_shard(endpoint, delay_tolerance=60):
    """
    :param endpoint: The endpoint of the SHARD to check
    :param delay_tolerance: The time (in seconds) that the shard timestamp can be behind
    :return: If shard is active or not
    """
    payload = """{
            "jsonrpc": "2.0",
            "method": "hmy_latestHeader",
            "params": [  ],
            "id": 1
        }"""
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        curr_time = datetime.datetime.utcnow()
        response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
        body = json.loads(response.content)
        time_str = body["result"]["timestamp"][:19] + '.0'  # Fit time format
        timestamp = datetime.datetime.strptime(time_str, util.datetime_format).replace(tzinfo=None)
        time_delta = curr_time - timestamp
        return abs(time_delta.seconds) < delay_tolerance
    except (requests.ConnectionError, json.decoder.JSONDecodeError, KeyError):
        return False


def add_key(name, passphrase='', verbose=False):
    proc = cli.expect_call(f"hmy keys add {name} --passphrase")
    process_passphrase(proc, passphrase, double=True)
    proc.wait()
    if verbose:
        print(f"Added account key with name: {name}")
    ACC_NAMES_ADDED.append(name)


def get_faucet_account(min_funds, endpoint):
    """
    Only looks for accounts that have funds on shard 0.
    """
    for acc_name in ACC_NAMES_ADDED:
        if float(get_balance(endpoint, name=acc_name)[0]["amount"]) >= min_funds:
            return acc_name
    raise RuntimeError(f"None of the loaded accounts have at least {min_funds} on shard 0")


def get_balance(node, name=None, address=None):
    assert name or address, "Must provide a keystore name or address"
    if not address:
        address = cli.get_address(name=name)
    assert address and address.startswith("one1")
    return json_load(cli.single_call(f"hmy --node={node} balances {address}"))


def process_passphrase(proc, passphrase, double=False):
    """
    This will enter the `passphrase` interactively given the pexpect child program, `proc`.
    """
    proc.expect("Enter passphrase:\r\n")
    proc.sendline(passphrase)
    if double:
        proc.expect("Repeat the passphrase:\r\n")
        proc.sendline(passphrase)
        proc.expect("\n")


def bls_generator(count, key_dir="/tmp", filter_fn=None, verbose=False):
    assert os.path.isabs(key_dir)
    if not os.path.exists(key_dir):
        os.makedirs(key_dir)
    if filter_fn is not None:
        assert callable(filter_fn)
        assert len(inspect.signature(filter_fn).parameters) == 1, "filter function must have 1 argument"

    for i in range(count):
        while True:
            if os.path.exists(f"{key_dir}/{ACC_NAME_PREFIX}bls{i}.key") and verbose:
                print(
                    f"{Typgpy.WARNING}Overriding BLS key file at: {key_dir}/{ACC_NAME_PREFIX}bls{i}.key {Typgpy.ENDC}")
            bls_key = json_load(cli.single_call(f"hmy keys generate-bls-key --bls-file-path "
                                                f"{key_dir}/{ACC_NAME_PREFIX}bls{i}.key", timeout=3))
            if filter_fn is None or filter_fn(bls_key):
                break
        if verbose:
            print(f"Generated BLS key:\n{json.dumps(bls_key, indent=4)}")
        yield bls_key


def is_after_epoch(n, endpoint):
    """
    :param n: The epoch number
    :param endpoint: The endpoint of the SHARD to check
    :return: If it is (strictly) after epoch N
    """
    try:
        return get_current_epoch(endpoint) > n
    except (requests.ConnectionError, json.decoder.JSONDecodeError, KeyError):
        return False


def get_shard_from_endpoint(endpoint):
    """
    Currently assumes <= 10 shards
    """
    re_match = re.search('\.s.\.', endpoint)
    if re_match:
        return int(re_match.group(0)[-2])
    re_match = re.search(':950./', endpoint)
    if re_match:
        return int(re_match.group(0)[-2])
    raise ValueError(f"Unknown endpoint format: {endpoint}")


def announce(fn):
    """
    Decorator to announce (via printing) that a function has been called.
    """

    def wrap(*args, **kwargs):
        print(f"{util.Typgpy.OKBLUE}{util.Typgpy.BOLD}Running: {fn.__name__}{util.Typgpy.ENDC}")
        return fn(*args, **kwargs)

    return wrap


def test(fn):
    """
    Test function wrapper.
    """

    def wrap(*args, **kwargs):
        print(f"\n{util.Typgpy.HEADER}"
              f"== Start test: {fn.__name__} =={util.Typgpy.ENDC}\n")
        try:
            to_be_returned = fn(*args, **kwargs)
            if to_be_returned:
                print(f"\n{util.Typgpy.HEADER}{util.Typgpy.UNDERLINE}"
                      f"== Passed test: {fn.__name__} =={util.Typgpy.ENDC}\n")
            else:
                print(f"\n{util.Typgpy.FAIL}{util.Typgpy.UNDERLINE}"
                      f"== FAILED test: {fn.__name__} =={util.Typgpy.ENDC}\n")
            return to_be_returned
        except Exception as e:  # Catch all to continue to other tests in same script.
            print(f"\n{util.Typgpy.FAIL}{util.Typgpy.UNDERLINE}"
                  f"== FAILED test: {fn.__name__} =={util.Typgpy.ENDC}\n")
            print(f"{util.Typgpy.FAIL}Exception:{e}\n")
            traceback.print_exc()
            print(util.Typgpy.ENDC)
            return False

    return wrap