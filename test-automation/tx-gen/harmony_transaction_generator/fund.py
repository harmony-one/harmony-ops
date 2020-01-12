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
        raise RuntimeError(f"No key in CLI's keystore has {funds} on shard {shard}")
    return accounts


def _group_accounts(accounts, bin_count):
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
    grouped_accounts = _group_accounts(accounts, len(account_pool))
    for j in range(len(account_pool)):
        threads.append(pool.apply_async(_fund, (account_pool[j], grouped_accounts[j],
                                                amount_per_account, shard_index)))
    for t in threads:
        transaction_hashes.extend(t.get())
    return transaction_hashes


def _fund_accounts(accounts, shard_index, amount):
    """
    Internal method to funds accounts, each account with sufficient funds will be threaded upon,
    until the max thread count is reached.
    """
    config = get_config()
    assert 0 <= shard_index < len(config["ENDPOINTS"])
    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    min_funding_balance = (config["ESTIMATED_GAS_PER_TXN"] + config['INIT_SRC_ACC_BAL_PER_SHARD']) * len(accounts)
    funding_accounts = sorted(_get_accounts_with_funds(min_funding_balance, shard_index),
                                     key=lambda e: account_balances[e][shard_index]["amount"], reverse=True)
    if len(funding_accounts) > max_threads:
        funding_accounts = funding_accounts[:max_threads]
        Loggers.general.warning(f"Have more funding accounts than configured threads, using top {max_threads} funded "
                                f"accounts on shard {shard_index} {[cli.get_address(n) for n in funding_accounts]}")
    assert funding_accounts, f"No validator in CLI's keystore has {min_funding_balance} on shard {shard_index}"
    transaction_hashes = _fund_accounts_from_account_pool(accounts, shard_index, amount, funding_accounts)
    return transaction_hashes


def fund_accounts(accounts, shard_indexes=None, amount=None):
    """
    :param accounts: An iterable of account names to be funded
    :param shard_indexes: An iterable of shard indexes that the accounts should be funded on.
                          Defaults to ALL shards    .
    :param amount: The amount to each accounts on each shard_index.
    """
    config = get_config()
    amount = config['INIT_SRC_ACC_BAL_PER_SHARD'] if not amount else amount
    if shard_indexes is None:
        shard_indexes = range(len(config["ENDPOINTS"]))
    assert hasattr(shard_indexes, "__iter__")
    for shard_index in shard_indexes:
        _fund_accounts(accounts, shard_index, amount)
