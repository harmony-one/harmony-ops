import json
import datetime

import requests

TIMESTAMP_FORMAT = '%Y-%m-%d %H:%M:%S %z %Z'


class COLOR:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_sharding_structure(endpoint):
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


def is_active_shard(endpoint, delay_tolerance=45):
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
        timestamp = datetime.datetime.strptime(body["result"]["timestamp"], TIMESTAMP_FORMAT).replace(tzinfo=None)
        time_delta = curr_time - timestamp
        return abs(time_delta.seconds) < delay_tolerance
    except (requests.ConnectionError, KeyError):
        return False


def is_after_epoch(n, endpoint):
    """
    :param n: The epoch number
    :param endpoint: The endpoint of the SHARD to check
    :return: If it is (strictly) after epoch N
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
        response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
        body = json.loads(response.content)
        return int(body["result"]["epoch"]) > n
    except (requests.ConnectionError, KeyError):
        return False


def announce(fn):
    """
    Simple decorator to announce (via printing) that a function has been called.
    """

    def wrap(*args):
        print(f"{COLOR.OKBLUE}{COLOR.BOLD}Running: {fn.__name__}{args}{COLOR.ENDC}")
        return fn(*args)

    return wrap


def test(fn):
    """
    Test function wrapper.
    :return If the test passed or not.
    """

    def wrap(*args):
        print(f"\n\t{COLOR.HEADER}== Start test: {fn.__name__} =={COLOR.ENDC}\n")
        if fn(*args):
            print(f"\n\t{COLOR.HEADER}{COLOR.UNDERLINE}== Passed test: {fn.__name__} =={COLOR.ENDC}\n")
            return True
        else:
            print(f"\n\t{COLOR.FAIL}{COLOR.UNDERLINE}== FAILED test: {fn.__name__} =={COLOR.ENDC}\n")
            return False

    return wrap
