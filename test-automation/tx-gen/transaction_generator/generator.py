import math
import random
import multiprocessing
import threading
from multiprocessing.pool import ThreadPool

from pyhmy import cli

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
_generator_pool = ThreadPool(processes=2)


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
    global _is_running

    if not _is_running:
        return
    _is_running = False
    for t in _generator_threads:
        t.get()
    _generator_pool.close()


def start(source_accounts, sink_accounts):
    global _generator_pool, _is_running
    config = get_config()

    if _is_running:
        return
    _is_running = True
    lock = threading.Lock()
    txn_count = 0

    def generate_transactions(src_accounts, snk_accounts):
        global _is_running
        nonlocal txn_count
        while _is_running and (config["MAX_TXN_GEN_COUNT"] is None or txn_count < config["MAX_TXN_GEN_COUNT"]):
            src_address = cli.get_address(random.choice(src_accounts))
            snk_address = cli.get_address(random.choice(snk_accounts))
            shard_choices = list(range(0, len(config["ENDPOINTS"])))
            src_shard = random.choices(shard_choices, weights=config["SRC_SHARD_WEIGHTS"], k=1)[0]
            snk_shard = random.choices(shard_choices, weights=config["SNK_SHARD_WEIGHTS"], k=1)[0]
            if config["ONLY_CROSS_SHARD"]:
                while src_shard == snk_shard:
                    src_shard = random.choices(shard_choices, weights=config["SRC_SHARD_WEIGHTS"], k=1)[0]
                    snk_shard = random.choices(shard_choices, weights=config["SNK_SHARD_WEIGHTS"], k=1)[0]
            txn_amt = random.uniform(config["AMT_PER_TXN"][0], config["AMT_PER_TXN"][1])
            send_transaction(src_address, snk_address, src_shard, snk_shard, txn_amt, wait=False)
            if config["MAX_TXN_GEN_COUNT"] is not None:
                lock.acquire()
                txn_count += 1
                lock.release()

    thread_count = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    thread_count = min(thread_count, len(source_accounts))
    k = max(len(source_accounts) // thread_count, 1)
    _generator_pool = ThreadPool(processes=thread_count)
    for i in range(thread_count):
        thread_src_accounts = source_accounts[i * k: (i + 1) * k]
        _generator_threads.append(_generator_pool
                                  .apply_async(generate_transactions, (thread_src_accounts, sink_accounts)))