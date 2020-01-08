import math
import random
import multiprocessing
from multiprocessing.pool import ThreadPool

from pyhmy import cli

from .common import (
    Loggers,
    config,
    import_account_name_prefix,
)
from .account_manager import (
    create_account,
    send_transaction
)

_is_running_benchmark = False
_benchmark_threads = []
_benchmark_pool = ThreadPool(processes=2)


def create_accounts(count, name_prefix="generated"):
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
    steps = int(count / max_threads)
    if count < 2:
        benchmarking_accounts = create(0, count)
    else:
        threads = []
        pool = ThreadPool(processes=max_threads)
        for i in range(max_threads):
            threads.append(pool.apply_async(create, (i * steps, (i + 1) * steps)))
        for t in threads:
            benchmarking_accounts.extend(t.get())
        benchmarking_accounts.extend(create(max_threads * steps, count))
        pool.close()
        pool.join()

    return benchmarking_accounts


def stop():
    global _is_running_benchmark

    if not _is_running_benchmark:
        return
    _is_running_benchmark = False
    for t in _benchmark_threads:
        t.get()
    _benchmark_pool.close()


def start(source_accounts, sink_accounts):
    global _benchmark_pool, _is_running_benchmark

    if _is_running_benchmark:
        return
    _is_running_benchmark = True

    def generate_transactions(src_accounts, snk_accounts):
        global _is_running_benchmark
        while _is_running_benchmark:
            src_address = cli.get_address(random.choice(src_accounts))
            snk_address = cli.get_address(random.choice(snk_accounts))
            src_shard = random.randint(0, config["SHARD_COUNT"] - 1)
            snk_shard = random.randint(0, config["SHARD_COUNT"] - 1)
            txn_amt = config["AMT_PER_TXN"]
            send_transaction(src_address, snk_address, src_shard, snk_shard,txn_amt, wait=False)

    thread_count = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    thread_count = min(thread_count, len(source_accounts))
    k = max(len(source_accounts) // thread_count, 1)
    _benchmark_pool = ThreadPool(processes=thread_count)
    for i in range(thread_count):
        thread_src_accounts = source_accounts[i * k: (i + 1) * k]
        if thread_src_accounts:
            _benchmark_threads.append(_benchmark_pool
                                      .apply_async(generate_transactions, (thread_src_accounts, sink_accounts)))
