import json
import datetime
import os
import time
from threading import Lock
from multiprocessing.pool import ThreadPool
from collections import defaultdict

import requests
from pyhmy.util import (
    json_load,
    datetime_format
)

from .common import (
    Loggers,
    get_config,
)


def live_info(accounts, interval, duration):
    # TODO: Function to get live (usable) feedback of current status of the tx-gen, during tx-gen.
    pass


def _get_transaction_by_hash(endpoint, txn_hash):
    """
    Internal get transaction by has to speed up analysis.
    Note that this functionality will eventually be migrated to the `pyhmy`
    """
    url = endpoint
    payload = "{\"jsonrpc\": \"2.0\", \"method\": \"hmy_getTransactionByHash\"," \
              "\"params\": [\"" + txn_hash + "\"],\"id\": 1}"
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=30)
    return json_load(response.content)


def verify_transactions(transaction_log_dir, start_time, end_time):
    """
    This will verify all transactions logged in `transaction_log_dir` from `start_time`
    (as a datetime obj in UTC) to `end_time` (as a datetime obj in UTC).

    It will return a report of the following structure:
    ```
        {
            "sent-transaction-report" : {
                "sent-transactions": {   # key = source shard
                    "0": [
                        <transaction log>
                    ],
                    "1": [
                        <transaction log>
                    ]
                },
                "sent-transactions-total": <count>,
                "sent-transactions-total-per-shard": {
                    "(<src_shard>, <dst_shard>)" : <count>
                },
                "failed-sent-transactions": {   # key = source shard
                    "0": [
                        <transaction log>
                    ],
                    "1": [
                        <transaction log>
                    ]
                },
                "failed-sent-transactions-total": <count>,
                "failed-sent-transactions-total-per-shard": {
                    "(<src_shard>, <dst_shard>)" : <count>
                }
            },
            "received-transaction-report" : {
                "successful-transactions": {  # key = source shard
                    "0": [
                        <transaction log>
                    ],
                    "1": [
                        <transaction log>
                    ]
                },
                "successful-transactions-total": <count>,
                "successful-transactions-total-per-shard": {
                    "(<src_shard>, <dst_shard>)" : <count>
                },
                "failed-transactions": {  # key = source shard
                    "0": [
                        <transaction log>
                    ],
                    "1": [
                        <transaction log>
                    ]
                },
                "failed-transactions-total": <count>,
                "failed-transactions-total-per-shard": {
                    "(<src_shard>, <dst_shard>)" : <count>
                }
            }
        }
    ```
    """
    config = get_config()
    transaction_log_dir = os.path.abspath(transaction_log_dir)
    assert os.path.isfile(transaction_log_dir)
    assert transaction_log_dir.endswith(".log")
    assert isinstance(start_time, datetime.datetime)
    assert isinstance(end_time, datetime.datetime)

    Loggers.report.info(f"{'='*6} Verifying transactions {'='*6}")
    with open(transaction_log_dir) as f:
        tokens = f.read().split("\n")

    transaction_logs = []
    for tok in tokens:
        if not tok:
            continue
        tok = tok.split(" : ")
        assert len(tok) == 2, f"Line format for `{transaction_log_dir}` is unknown,"
        txn_log = json.loads(tok[1].strip())
        date = datetime.datetime.strptime(txn_log["send-time-utc"], datetime_format)
        if date >= end_time:
            break
        if date >= start_time:
            transaction_logs.append(txn_log)

    sent_txn_hashes = set()
    sent_txn_per_shard = defaultdict(list)
    sent_shard_txn_total = defaultdict(int)

    failed_sent_txn_count = 0
    failed_sent_txn_per_shard = defaultdict(list)
    failed_sent_shard_txn_total = defaultdict(int)

    for txn_log in transaction_logs:
        txn_hash = txn_log["hash"]
        src, dst = str(txn_log["from-shard"]), str(txn_log["to-shard"])
        if txn_hash is None:
            failed_sent_txn_count += 1
            failed_sent_shard_txn_total[f"({src}, {dst})"] += 1
            failed_sent_txn_per_shard[src].append(txn_log)
        elif txn_hash not in sent_txn_hashes:
            sent_txn_hashes.add(txn_hash)
            sent_shard_txn_total[f"({src}, {dst})"] += 1
            sent_txn_per_shard[src].append(txn_log)

    sent_transaction_report = {
        "sent-transactions-total": len(sent_txn_hashes),
        "sent-transactions": sent_txn_per_shard,
        "sent-transactions-total-per-shard": sent_shard_txn_total,
        "failed-sent-transactions-total": failed_sent_txn_count,
        "failed-sent-transactions": failed_sent_txn_per_shard,
        "failed-sent-transactions-total-per-shard": failed_sent_shard_txn_total,
    }
    Loggers.report.info(json.dumps(sent_transaction_report, indent=4))

    successful_txn_count = 0
    successful_txn_shard_count = defaultdict(int)
    successful_txn_per_shard = defaultdict(list)
    failed_txn_count = 0
    failed_txn_shard_count = defaultdict(int)
    failed_txn_per_shard = defaultdict(list)
    lock = Lock()

    def check_hash(src_shard, dst_shard, src_endpoint, log):
        nonlocal successful_txn_count, failed_txn_count
        response = _get_transaction_by_hash(src_endpoint, log['hash'])
        lock.acquire()
        if response['result'] is not None:
            successful_txn_count += 1
            successful_txn_shard_count[f"({src_shard}, {dst_shard})"] += 1
            successful_txn_per_shard[shard].append(log)
        else:
            failed_txn_count += 1
            failed_txn_shard_count[f"({src_shard}, {dst_shard})"] += 1
            failed_txn_per_shard[shard].append(log)
        lock.release()

    pool = ThreadPool()
    threads = []
    for shard, txn_log_list in sent_txn_per_shard.items():
        endpoint = config["ENDPOINTS"][int(shard)]
        for txn_log in txn_log_list:
            src, dst = str(txn_log["from-shard"]), str(txn_log["to-shard"])
            threads.append(pool.apply_async(check_hash, (src, dst, endpoint, txn_log)))
    for t in threads:
        t.get()
    pool.close()

    received_transaction_report = {
        "successful-transactions-total": successful_txn_count,
        "successful-transactions": successful_txn_per_shard,
        "successful-transactions-total-per-shard": successful_txn_shard_count,
        "failed-transactions-total": failed_txn_count,
        "failed-transactions": failed_txn_per_shard,
        "failed-transactions-total-per-shard": failed_txn_shard_count,
    }
    Loggers.report.info(json.dumps(received_transaction_report, indent=4))
    Loggers.report.write()
    report = {
        "sent-transaction-report": sent_transaction_report,
        "received-transaction-report": received_transaction_report
    }
    return report
