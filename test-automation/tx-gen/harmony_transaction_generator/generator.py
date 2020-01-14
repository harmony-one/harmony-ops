import math
import random
import multiprocessing
import itertools
from threading import Lock
from multiprocessing.pool import ThreadPool

from pyhmy import cli
from pyhmy import util
import requests

from .common import (
    Loggers,
    get_config,
    import_account_name_prefix,
)
from .account_manager import (
    create_account,
    send_transaction
)

_is_running = False
_generator_threads = []
_generator_pool = ThreadPool()


def _get_nonce(endpoint, address):
    """
    Internal get nonce to bypass subprocess latency of calling CLI.
    """
    url = endpoint
    payload = "{\"jsonrpc\": \"2.0\", \"method\": \"hmy_getTransactionCount\"," \
              "\"params\": [\"" + address + "\", \"latest\"],\"id\": 1}"
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=30)
    return int(util.json_load(response.content)["result"], 16)


def create_accounts(count, name_prefix="generated"):
    config = get_config()
    assert count > 0
    benchmarking_accounts = []

    def create(start_i, end_i):
        local_accounts = []
        for j in range(start_i, end_i):
            acc_name = f"{import_account_name_prefix}{name_prefix}_{j}"
            create_account(acc_name)
            Loggers.general.info(f"Created account: {cli.get_address(acc_name)} ({acc_name})")
            local_accounts.append(acc_name)
        return local_accounts

    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    max_threads = min(count, max_threads)
    steps = int(math.ceil(count / max_threads))
    if count < 2:
        benchmarking_accounts = create(0, count)
    else:
        threads = []
        pool = ThreadPool(processes=max_threads)
        for i in range(max_threads):
            threads.append(pool.apply_async(create, (i * steps, min(count, (i + 1) * steps))))
        for t in threads:
            benchmarking_accounts.extend(t.get())
        pool.close()
        pool.join()

    return benchmarking_accounts


def stop():
    """
    Stops the transaction generation.
    """
    global _is_running

    if not _is_running:
        return
    _is_running = False
    for t in _generator_threads:
        t.get()
    _generator_pool.close()


def start(source_accounts, sink_accounts):
    """
    Starts the transaction generation where for each transaction:
        The source account is chosen at random from the pool of accounts, `source_accounts`
        The sink / destination account is chosen at random from the pool of accounts, `sink_accounts`
        The to and from shards are chosen at random as defined by the shard weights in the config.

    :param source_accounts: A list that defines the pool of source accounts
    :param sink_accounts: A list that defines the pool of sink accounts
    """
    global _generator_pool, _is_running
    config = get_config()
    endpoints = config["ENDPOINTS"]

    if _is_running:
        return
    _is_running = True
    lock = Lock()
    txn_count = 0

    def generate_transactions(src_accounts, snk_accounts):
        global _is_running
        nonlocal txn_count
        ref_nonce = {n: [(_get_nonce(endpoints[j], n), Lock()) for j in range(len(endpoints))] for n in src_accounts}
        src_accounts_iter = itertools.cycle(src_accounts)
        while _is_running:
            src_name = next(src_accounts_iter)
            src_address = cli.get_address(src_name)
            snk_address = cli.get_address(random.choice(snk_accounts))
            shard_choices = list(range(0, len(config["ENDPOINTS"])))
            src_shard = random.choices(shard_choices, weights=config["SRC_SHARD_WEIGHTS"], k=1)[0]
            snk_shard = random.choices(shard_choices, weights=config["SNK_SHARD_WEIGHTS"], k=1)[0]
            retry_count = 0
            if config["ONLY_CROSS_SHARD"]:
                while src_shard == snk_shard:
                    if config["MAX_TXN_GEN_COUNT"] is not None and txn_count >= config["MAX_TXN_GEN_COUNT"]:
                        return  # quit early if txn_count happens to exceed max, true check is done when txn is sent
                    if retry_count > 50:
                        Loggers.general.warning("Trying to force 'from' and 'to' shards to be different, "
                                                "are source and sink shard weights correct in config?")
                        Loggers.general.write()
                    src_shard = random.choices(shard_choices, weights=config["SRC_SHARD_WEIGHTS"], k=1)[0]
                    snk_shard = random.choices(shard_choices, weights=config["SNK_SHARD_WEIGHTS"], k=1)[0]
                    retry_count += 1
            txn_amt = random.uniform(config["AMT_PER_TXN"][0], config["AMT_PER_TXN"][1])
            if config["MAX_TXN_GEN_COUNT"] is not None:
                lock.acquire()
                if txn_count >= config["MAX_TXN_GEN_COUNT"]:
                    lock.release()
                    return
                txn_count += 1
                lock.release()
            curr_nonce = _get_nonce(endpoints[src_shard], src_address)
            n, n_lock = ref_nonce[src_name][src_shard]
            n_lock.acquire()
            if curr_nonce < n:
                n_lock.release()
                continue
            ref_nonce[src_name][src_shard][0] += 1
            n_lock.release()
            send_transaction(src_address, snk_address, src_shard, snk_shard, txn_amt, wait=False)

    thread_count = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    thread_count = min(thread_count, len(source_accounts))
    k = max(len(source_accounts) // thread_count, 1)
    _generator_pool = ThreadPool(processes=thread_count)
    for i in range(thread_count):
        thread_src_accounts = source_accounts[i * k: (i + 1) * k]
        _generator_threads.append(_generator_pool
                                  .apply_async(generate_transactions, (thread_src_accounts, sink_accounts)))
