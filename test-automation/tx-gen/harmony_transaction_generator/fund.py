import random
import math
import multiprocessing
import time
from multiprocessing.pool import ThreadPool

from pyhmy import cli

from .common import (
    Loggers,
    get_config,
    import_account_name_prefix
)
from .account_manager import (
    create_account,
    send_transaction,
    return_balances,
    account_balances,
)


def _get_accounts_with_funds(funds, shard):
    def fund_filter(el):
        _, value = el
        if type(value) != list or value[shard]["shard"] != shard:
            return False
        return value[shard]["amount"] >= funds

    accounts = [k for k, v in filter(fund_filter, account_balances.items())]
    if not accounts:
        raise RuntimeError(f"No validator in CLI's keystore has {funds} on shard {shard}")
    return accounts


def _group_accounts_(accounts, bin_count):
    grouped_accounts = [[] for _ in range(bin_count)]
    accounts_iter = iter(accounts)
    i = 0
    while i < len(accounts):
        for j in range(bin_count):
            i += 1
            acc = next(accounts_iter, None)
            if acc is None:
                break
            grouped_accounts[j].append(acc)
    return grouped_accounts


def _fund(src_acc, accounts, amount, shard_index, safe=True):
    transaction_hashes = []
    for account in accounts:
        from_address = cli.get_address(src_acc)
        to_address = cli.get_address(account)
        Loggers.general.info(f"Funding {to_address} ({account}) for shard {shard_index}")
        txn_hash = send_transaction(from_address, to_address, shard_index, shard_index,
                                    amount, retry=True, wait=safe)
        transaction_hashes.append(txn_hash)
    return transaction_hashes


def _fund_accounts_from_account_pool(accounts, shard_index, amount_per_account, account_pool):
    """
    Assume funding accounts have enough funds to account for gas.
    """
    pool = ThreadPool(len(account_pool))
    transaction_hashes = []
    threads = []
    grouped_accounts = _group_accounts_(accounts, len(account_pool))
    for j in range(len(account_pool)):
        threads.append(pool.apply_async(_fund,
                                        (account_pool[j], grouped_accounts[j], amount_per_account, shard_index)))
    for t in threads:
        transaction_hashes.extend(t.get())
    return transaction_hashes


def _fund_accounts(accounts, shard_index):
    """
    Internal method to fund accounts using middlemen (if threshold is met)
    """
    config = get_config()
    assert 0 <= shard_index < len(config["ENDPOINTS"])
    transaction_hashes = []
    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    accounts_per_middleman = config["NUM_SRC_ACC"] // max_threads
    remaining_accounts_count = config["NUM_SRC_ACC"] % max_threads
    if accounts_per_middleman < 2:  # Set the threshold for using middlemen
        accounts_per_middleman = 0
        remaining_accounts_count = len(accounts)

    if accounts_per_middleman:
        fund_account_list = accounts[:accounts_per_middleman * max_threads]
        middleman_accounts = [f"{import_account_name_prefix}middleman{i}" for i in range(max_threads)]
        threads = []
        pool = ThreadPool(processes=max_threads)
        for acc in middleman_accounts:
            threads.append(pool.apply_async(create_account, (acc,)))
        for t in threads:
            t.get()
        pool.close()

        amount_per_middleman = accounts_per_middleman * (config['INIT_SRC_ACC_BAL_PER_SHARD']
                                                         + config["ESTIMATED_GAS_PER_TXN"])
        min_funding_balance = (config["ESTIMATED_GAS_PER_TXN"] + amount_per_middleman) * len(accounts)
        funding_accounts = _get_accounts_with_funds(min_funding_balance, shard_index)
        _fund_accounts_from_account_pool(middleman_accounts, shard_index, amount_per_middleman, funding_accounts)
        transaction_hashes.extend(_fund_accounts_from_account_pool(fund_account_list, shard_index,
                                                                   config['INIT_SRC_ACC_BAL_PER_SHARD'],
                                                                   middleman_accounts))
        return_balances(middleman_accounts)
    if remaining_accounts_count:
        fund_account_list = accounts[-remaining_accounts_count:]
        min_funding_balance = (config["ESTIMATED_GAS_PER_TXN"]
                               + config['INIT_SRC_ACC_BAL_PER_SHARD']) * len(fund_account_list)
        funding_accounts = _get_accounts_with_funds(min_funding_balance, shard_index)
        funding_accounts_set = set(funding_accounts)
        for acc in accounts:
            if acc in funding_accounts_set:
                funding_accounts.remove(acc)
        assert funding_accounts, f"No validator in CLI's keystore has {min_funding_balance} on shard {shard_index}"
        transaction_hashes.extend(_fund_accounts_from_account_pool(fund_account_list, shard_index,
                                                                   config['INIT_SRC_ACC_BAL_PER_SHARD'],
                                                                   funding_accounts))
    return transaction_hashes


def fund_accounts(accounts, shard_indexes=None):
    """
    :param accounts: An iterable of account names to be funded
    :param shard_indexes: An iterable of shard indexes that the accounts should be funded on.
                          Defaults to ALL shards.
    """
    config = get_config()
    if shard_indexes is None:
        shard_indexes = range(len(config["ENDPOINTS"]))
    assert hasattr(shard_indexes, "__iter__")
    for shard_index in shard_indexes:
        _fund_accounts(accounts, shard_index=shard_index)
