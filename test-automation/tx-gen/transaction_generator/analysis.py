import json
import datetime
import os
import re
from collections import defaultdict

import requests
from pyhmy.util import (
    json_load,
    datetime_format
)

from .common import (
    Loggers,
    config,
)


def live_info(accounts, log, interval, duration):
    # TODO: improve this so that we have better data as to what is going on.
    assert isinstance(log, ControlledLogger)
    assert accounts
    last_totals = [[0.0] * config["SHARD_COUNT"] for _ in range(len(accounts))]
    diffs = [[list() for _ in range(config["SHARD_COUNT"])] for _ in range(len(accounts))]
    end_time = time.time() + duration
    start_time = time.time()
    while start_time < end_time:
        log.info(f"==== Txn Count Info ====")
        log.info(f"Check interval: {interval}")
        for i, account in enumerate(accounts):
            balances = get_balance(account)
            for shard in range(config["SHARD_COUNT"]):
                total = math.ceil(balances[shard]["amount"] / config["AMT_PER_TXN"])
                diff = total - last_totals[i][shard]
                last_totals[i][shard] = total
                diffs[i][shard].append(diff)
                average = math.ceil(sum(diffs[i][shard]) / len(diffs[i][shard]))
                log.info(f"-----")
                log.info(f"Account: {cli.get_address(account)}")
                log.info(f"Shard: {shard}")
                log.info(f"Shard balance: {balances[shard]['amount']}")
                log.info(f"Total Txn: {total}")
                log.info(f"Diff: {diff}")
                log.info(f"Curr Avg: {average} txn per {interval} seconds")
                log.info(f"-----")
        log.info(f"=============================")
        sleep_time = interval - (time.time() - start_time)
        if sleep_time > 0:
            time.sleep(sleep_time)
        start_time = time.time()
    return last_totals, diffs


def get_transaction_by_hash(endpoint, txn_hash):
    url = endpoint
    payload = "{\"jsonrpc\": \"2.0\", \"method\": \"hmy_getTransactionByHash\"," \
              "\"params\": [\"" + txn_hash + "\"],\"id\": 1}"
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json_load(response.content)


def verify_transactions(transaction_log_dir, start_time, end_time):
    # TODO: documentation
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
        match = re.search(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}.\d{6}', tok[0])
        assert match, f"time format for `{transaction_log_dir}` not found or unknown."
        date = datetime.datetime.strptime(match.group(), datetime_format)
        if date >= end_time:
            break
        if date >= start_time:
            transaction_hashes.append(json.loads(tok[1].strip()))

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
            Loggers.report.info(f"checking {curr_count} / {len(sent_txn_hashes)} transactions")
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
