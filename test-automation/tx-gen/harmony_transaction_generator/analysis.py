import json
import datetime
import os
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
    # TODO: Function to get life (usable) feedback of current status of the tx-gen, during tx-gen.
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
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json_load(response.content)


def verify_transactions(transaction_log_dir, start_time, end_time):
    """
    :param transaction_log_dir: The file path to the log file of transactions
    :param start_time: The start time (as a datetime object) of the transactions to verify in UTC
    :param end_time: The end time (as a datetime object) of the transactions to verify in UTC
    :return: A report with the following structure:
        ex:
        {
            "sent-transaction-report" : {
                "sent-transactions": {
                    "0": [
                        <transaction hashes>
                    ],
                    "1": [
                        <transaction hashes>
                    ]
                },
                "sent-transactions-total": 15,
                "sent-transactions-total-per-shard": {
                    "(<src_shard>, <dst_shard>)" : <count>
                }
            },
            "received-transaction-report" : {
                "successful-transactions": {  # key = source shard
                    "0": [
                        <transaction hashes>
                    ],
                    "1": [
                        <transaction hashes>
                    ]
                },
                "successful-transactions-total": 8,
                "successful-transactions-total-per-shard": {
                    "0": 4,
                    "1": 4
                },
                "failed-transactions": {  # key = source shard
                    "0": [
                        <transaction hashes>
                    ],
                    "1": [
                        <transaction hashes>
                    ]
                },
                "failed-transactions-total": 7,
                "failed-transactions-total-per-shard": {
                    "0": 3,
                    "1": 4
                }
            }
        }
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

    transaction_hashes = []
    for tok in tokens:
        if not tok:
            continue
        tok = tok.split(" : ")
        assert len(tok) == 2, f"Line format for `{transaction_log_dir}` is unknown,"
        txn_log = json.loads(tok[1].strip())
        date = datetime.datetime.strptime(txn_log["time-utc"], datetime_format)
        if date >= end_time:
            break
        if date >= start_time:
            transaction_hashes.append(txn_log)

    sent_txn_hashes = set()
    sent_txn_per_shard = defaultdict(list)
    sent_shard_txn_total = defaultdict(int)

    for txn in transaction_hashes:
        txn_hash = txn["hash"]
        if txn_hash not in sent_txn_hashes:
            sent_txn_hashes.add(txn_hash)
            src_shard, dst_shard = str(txn["from-shard"]), str(txn["to-shard"])
            sent_shard_txn_total[f"({src_shard}, {dst_shard})"] += 1
            sent_txn_per_shard[src_shard].append(txn_hash)

    sent_transaction_report = {
        "sent-transactions": sent_txn_per_shard,
        "sent-transactions-total": len(sent_txn_hashes),
        "sent-transactions-total-per-shard": sent_shard_txn_total,
    }
    Loggers.report.info(json.dumps(sent_transaction_report, indent=4))

    successful_txn_count = 0
    successful_txn_per_shard = defaultdict(list)
    successful_shard_txn_total = defaultdict(int)
    failed_txn_count = 0
    failed_txn_per_shard = defaultdict(list)
    failed_shard_txn_total = defaultdict(int)
    curr_count = 0
    for shard, shard_txn_hashes in sent_txn_per_shard.items():
        endpoint = config["ENDPOINTS"][int(shard)]
        for h in shard_txn_hashes:
            response = _get_transaction_by_hash(endpoint, h)
            Loggers.general.info(f"checking {curr_count} / {len(sent_txn_hashes)} transactions")
            curr_count += 1
            if response['result'] is not None:
                successful_txn_count += 1
                successful_shard_txn_total[shard] += 1
                successful_txn_per_shard[shard].append(h)
            else:
                failed_txn_count += 1
                failed_shard_txn_total[shard] += 1
                failed_txn_per_shard[shard].append(h)

    received_transaction_report = {
        "successful-transactions": successful_txn_per_shard,
        "successful-transactions-total": successful_txn_count,
        "successful-transactions-total-per-shard": successful_shard_txn_total,
        "failed-transactions": failed_txn_per_shard,
        "failed-transactions-total": failed_txn_count,
        "failed-transactions-total-per-shard": failed_shard_txn_total,
    }
    Loggers.report.info(json.dumps(received_transaction_report, indent=4))
    Loggers.report.write()
    report = {
        "sent-transaction-report": sent_transaction_report,
        "received-transaction-report": received_transaction_report
    }
    return report
