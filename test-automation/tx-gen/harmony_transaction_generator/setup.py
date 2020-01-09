import random
import math
import multiprocessing
from multiprocessing.pool import ThreadPool

from pyhmy import cli

from .common import (
    Loggers,
    get_config,
    import_account_name_prefix,
)
from .account_manager import (
    is_fast_loaded,
    get_fast_loaded_passphrase,
    create_account,
    send_transaction,
    return_balances,
    remove_accounts,
    account_balances
)


def _fund_middlemen(shard_index):
    """
    Internal helper method for 'fund_accounts' which returns a list of funded middlemen
    as needed by the constraints set in the CONFIG file.

    Middlemen accounts are used to parallelize funding source accounts without changing
    the nonce explicitly. It also helps deal with the probably nonce missmatch of
    multiple nodes in the start funding source accounts from the same pool of accounts.
    """
    config = get_config()
    assert 0 <= shard_index < len(config["ENDPOINTS"])
    total_funds_needed = config["NUM_SRC_ACC"] * config["INIT_SRC_ACC_BAL_PER_SHARD"]
    middleman_count = min(config["MAX_THREAD_COUNT"], config["NUM_SRC_ACC"])
    funds_per_middleman = total_funds_needed / middleman_count
    middleman_gas_overhead = (2 * config["ESTIMATED_GAS_PER_TXN"]) * math.ceil(config["NUM_SRC_ACC"] / middleman_count)
    min_funding_balance = (config["ESTIMATED_GAS_PER_TXN"] + middleman_gas_overhead) * middleman_count
    min_funding_balance += total_funds_needed

    Loggers.general.info(f"Funding {middleman_count} middlemen accounts for shard {shard_index}")
    Loggers.general.info(f"Total funds needed for all middlemen on shard {shard_index}: {min_funding_balance}")

    def fund_filter(el):
        _, value = el
        if type(value) != list or value[shard_index]["shard"] != shard_index:
            return False
        return value[shard_index]["amount"] >= min_funding_balance

    funding_accounts = [k for k, v in filter(fund_filter, account_balances.items())]
    if not funding_accounts:
        raise RuntimeError(f"No validator in CLI's keystore has {min_funding_balance} on shard {shard_index}")

    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    max_threads = min(max_threads, middleman_count, int(math.ceil(len(funding_accounts)/3)))
    bin_size = len(funding_accounts) // max_threads
    binned_funding_accounts = [funding_accounts[i:i + bin_size] for i in range(0, len(funding_accounts), bin_size)]

    def create_and_fund(amount, funded_accounts):
        funding_acc_name = random.choice(funded_accounts)
        middleman_acc_name = f"{import_account_name_prefix}middle_man{random.randint(-1e6, 1e6)}"
        create_account(middleman_acc_name)
        from_address = cli.get_address(funding_acc_name)
        to_address = cli.get_address(middleman_acc_name)
        amount += middleman_gas_overhead
        passphrase = get_fast_loaded_passphrase(funding_acc_name) if is_fast_loaded(funding_acc_name) else ''
        Loggers.general.info(f"Funding middleman: {to_address} ({middleman_acc_name}) for shard {shard_index}")
        send_transaction(from_address, to_address, shard_index, shard_index, amount, passphrase, retry=True)
        return middleman_acc_name

    total_middlemen_to_fund = middleman_count
    middleman_accounts = []
    pool = ThreadPool(processes=max_threads)
    while total_middlemen_to_fund > 0:
        threads = []
        for i in range(min(max_threads, total_middlemen_to_fund)):
            threads.append(pool.apply_async(create_and_fund, (funds_per_middleman, binned_funding_accounts[i])))
            total_middlemen_to_fund -= 1
        for t in threads:
            middleman_accounts.append(t.get())
    pool.close()
    pool.join()
    return middleman_accounts


def _fund_accounts(accounts, shard_index):
    config = get_config()
    assert 0 <= shard_index < len(config["ENDPOINTS"])
    transaction_hashes = []
    middleman_accounts = _fund_middlemen(shard_index)

    def fund(src_acc, _accounts):
        for account in _accounts:
            from_address = cli.get_address(src_acc)
            to_address = cli.get_address(account)
            amount = config['INIT_SRC_ACC_BAL_PER_SHARD']
            Loggers.general.info(f"Funding {to_address} ({account}) for shard {shard_index}")
            txn_hash = send_transaction(from_address, to_address, shard_index, shard_index, amount, retry=True)
            transaction_hashes.append(txn_hash)

    grouped_accounts = [[] for _ in range(len(middleman_accounts))]
    accounts_iter = iter(accounts)
    i = 0
    while i < len(accounts):
        for j in range(len(middleman_accounts)):
            i += 1
            acc = next(accounts_iter, None)
            if acc is None:
                break
            grouped_accounts[j].append(acc)

    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    for i in range(0, len(middleman_accounts), max_threads):
        threads = []
        pool = ThreadPool(processes=max_threads)
        for j in range(i, min(i + max_threads, len(middleman_accounts))):
            threads.append(pool.apply_async(fund, (middleman_accounts[j], grouped_accounts[j])))
        for t in threads:
            t.get()
        pool.close()
        pool.join()

    return_balances(middleman_accounts)
    remove_accounts(middleman_accounts)
    return transaction_hashes


def fund_accounts(accounts, shard_indexes=None):
    config = get_config()
    if shard_indexes is None:
        shard_indexes = range(len(config["ENDPOINTS"]))
    assert hasattr(shard_indexes, "__iter__")
    for shard_index in shard_indexes:
        _fund_accounts(accounts, shard_index=shard_index)
