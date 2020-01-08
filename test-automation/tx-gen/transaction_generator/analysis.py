import json
import time
import math
from collections import defaultdict

import requests
from pyhmy import cli
from pyhmy.logging import (
    ControlledLogger
)
from pyhmy.util import (
    json_load
)

from .common import (
    Loggers,
    config,
)
from .account_manager import (
    get_balance
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


def verify_transactions(endpoints, transaction_log_dir, txn_counts, differences, log):
    log.info("Verifying transactions...")
    with open(transaction_log_dir) as f:
        toks = f.read().split("\n")
    benchmark_txn = []
    start_benchmark = False
    for tok in toks:
        tok = tok.split(" : ")
        if len(tok) != 2:
            continue
        if '=' in tok[1]:
            start_benchmark = True
            continue
        if not start_benchmark:
            continue
        if start_benchmark and tok[1] == "Finished Benchmark...":
            break
        benchmark_txn.append(json.loads(tok[1].strip()))

    sent_txn_hashes = set()
    sent_txn_per_shard = defaultdict(list)
    sent_shard_txn_total = defaultdict(int)

    for txn in benchmark_txn:
        txn_hash = txn["hash"]
        if txn_hash not in sent_txn_hashes:
            sent_txn_hashes.add(txn_hash)
            src_shard, dst_shard = str(txn["from-shard"]), str(txn["to-shard"])
            sent_shard_txn_total[f"{src_shard},{dst_shard}"] += 1
            sent_txn_per_shard[src_shard].append(txn_hash)

    info = {
        "sent-transactions": sent_txn_per_shard,
        "sent-transactions-total": len(sent_txn_hashes),
        "sent-transactions-total-per-shard": sent_shard_txn_total,
    }
    Loggers.report.info(json.dumps(info))

    successful_txn_count = 0
    successful_txn_per_shard = defaultdict(list)
    successful_shard_txn_total = defaultdict(int)
    failed_txn_count = 0
    failed_txn_per_shard = defaultdict(list)
    failed_shard_txn_total = defaultdict(int)
    curr_count = 0
    for shard, shard_txn_hashes in sent_txn_per_shard.items():
        endpoint = endpoints[int(shard)]
        for h in shard_txn_hashes:
            response = get_transaction_by_hash(endpoint, h)
            log.info(f"checking {curr_count} / {len(sent_txn_hashes)} transactions")
            curr_count += 1
            if response['result'] is not None:
                successful_txn_count += 1
                successful_shard_txn_total[shard] += 1
                successful_txn_per_shard[shard].append(h)
            else:
                failed_txn_count += 1
                failed_shard_txn_total[shard] += 1
                failed_txn_per_shard[shard].append(h)

    info = {
        "balance-txn-counts": txn_counts,
        "successful-transactions": successful_txn_per_shard,
        "successful-transactions-total": successful_txn_count,
        "successful-transactions-total-per-shard": successful_shard_txn_total,
        "failed-transactions": failed_txn_per_shard,
        "failed-transactions-total": failed_txn_count,
        "failed-transactions-total-per-shard": failed_shard_txn_total,
    }
    Loggers.report.info(json.dumps(info))
