import os
import shutil
import math
import multiprocessing
import json
import datetime
from multiprocessing.pool import ThreadPool

from pyhmy import cli
from pyhmy.util import (
    json_load
)

from .common import (
    Loggers,
    get_config,
    import_account_name_prefix,
)

account_balances = {}

_accounts_added = set()
_fast_loaded_accounts = {}  # keys = acc_names, values = passphrase


def get_balances(account_name, shard_index=0):
    config = get_config()
    assert shard_index < len(config["ENDPOINTS"])
    address = cli.get_address(account_name)
    if not address:
        return {}
    response = cli.single_call(f"hmy balances {address} --node={config['ENDPOINTS'][shard_index]}", timeout=15)
    balances = json_load(response.replace("\n", ""))
    info = {'address': address, 'balances': balances, 'time-utc': str(datetime.datetime.utcnow())}
    Loggers.balance.info(json.dumps(info))
    account_balances[account_name] = balances
    return balances


def load_accounts(keystore_path, passphrase, name_prefix="import", fast_load=False):
    """
    :param keystore_path: The path to the keystore to import. Note the specific format of the keystore,
                          Reference './localnet_validator_keys/'.
    :param passphrase: The passphrase for ALL keys in the keystore.
    :param name_prefix: The name assigned to each account in the CLI's keystore.
    :param fast_load: Copy over the file instead of importing the file using `import-ks`.
    :return: A list of account names (in the CLI's keystore) that were added.
    """
    config = get_config()
    assert os.path.exists(keystore_path)
    keystore_path = os.path.realpath(keystore_path)
    key_paths = os.listdir(keystore_path)
    accounts_added = []

    def load(start, end):
        for j, file_name in enumerate(key_paths[start: end]):
            # STRONG assumption about imported key-files.
            if file_name.endswith(".key") or not file_name.startswith("."):
                file_path = f"{keystore_path}/{file_name}"
                account_name = f"{import_account_name_prefix}{name_prefix}{j+start}"
                if not cli.get_address(account_name):
                    cli.remove_account(account_name)  # Just in-case there is a folder with nothing in it.
                    Loggers.general.info(f"Adding key file: ({j+start}) {file_name}")
                    if fast_load:
                        keystore_acc_dir = f"{cli.get_account_keystore_path()}/{account_name}"
                        os.makedirs(keystore_acc_dir, exist_ok=True)
                        shutil.copy(file_path, f"{keystore_acc_dir}/{file_name}")
                        _fast_loaded_accounts[account_name] = passphrase
                    else:
                        cli.single_call(f"hmy keys import-ks {file_path} {account_name} "
                                        f"--passphrase={passphrase}")
                accounts_added.append(account_name)
                _accounts_added.add(account_name)
                account_balances[account_name] = get_balances(account_name)

    max_threads = multiprocessing.cpu_count() if not config['MAX_THREAD_COUNT'] else config['MAX_THREAD_COUNT']
    max_threads = min(max_threads, len(key_paths))
    steps = int(math.ceil(len(key_paths) / max_threads))

    threads = []
    pool = ThreadPool(processes=max_threads)
    for i in range(max_threads):
        threads.append(pool.apply_async(load, (i * steps, (i + 1) * steps)))
    for t in threads:
        t.get()
    pool.close()
    pool.join()
    return accounts_added


def create_account(account_name):
    cli.remove_account(account_name)
    cli.single_call(f"hmy keys add {account_name}")
    get_balances(account_name)
    _accounts_added.add(account_name)
    return account_name


def is_fast_loaded(account_name):
    return account_name in _fast_loaded_accounts.keys()


def get_fast_loaded_passphrase(account):
    if account.startswith("one1"):
        account_names = cli.get_accounts(account)
        if account_names:
            account = account_names[0]
        else:
            return
    return _fast_loaded_accounts.get(account, None)


def remove_accounts(accounts, backup=True):
    """
    TODO: remove logging private keys
    :param accounts: An iterable of accounts names to remove
    :param backup: If true, logs (to the general logger) the private key of the account that was removed.
    """
    for acc in accounts:
        address = cli.get_address(acc)
        private_key = ""
        if backup:
            try:
                private_key = cli.single_call(f"hmy keys export-private-key {address}").strip()
            except RuntimeError:
                Loggers.general.error(f"{address} ({acc}) was not imported via CLI, cannot backup")
                private_key = "NOT-IMPORTED-USING-CLI"
        cli.remove_account(acc)
        if acc in _accounts_added:
            _accounts_added.remove(acc)
        if acc in _fast_loaded_accounts:
            del _fast_loaded_accounts[acc]
        removed_account = {"address": address, "private-key": private_key}
        Loggers.general.info(f"Removed Account: {removed_account}")


def send_transaction(from_address, to_address, src_shard, dst_shard, amount,
                     pw='', wait=True, retry=False, max_tries=5):
    config = get_config()
    assert cli.check_address(from_address), "source address must be in the CLI's keystore."
    attempt_count = 0
    command = f"hmy --node={config['ENDPOINTS'][src_shard]} transfer " \
              f"--from={from_address} --to={to_address} " \
              f"--from-shard={src_shard} --to-shard={dst_shard} " \
              f"--amount={amount} --passphrase={pw} --chain-id={config['CHAIN_ID']} "
    if wait:
        command += f"--wait-for-confirm {config['TXN_WAIT_TO_CONFIRM']}"
    while True:
        try:
            response = cli.single_call(command, timeout=config['TXN_WAIT_TO_CONFIRM']).strip()
            if wait:
                txn_hash = json_load(response)["result"]["transactionHash"]
            else:
                txn_hash = json_load(response)["transaction-receipt"]
            info = {
                'from': from_address, 'to': to_address,
                'from-shard': src_shard, 'to-shard': dst_shard,
                'amount': amount, 'hash': txn_hash, 'time-utc': str(datetime.datetime.utcnow())
            }
            Loggers.transaction.info(json.dumps(info))
            return txn_hash
        except (RuntimeError, json.JSONDecodeError) as e:
            if not retry or attempt_count >= max_tries:
                raise e
            attempt_count += 1
            Loggers.general.warning(f"[Trying Again] Failure sending from {from_address} (s{src_shard}) "
                                    f"to {to_address} (s{dst_shard})\n"
                                    f"\tError: {e}")


def return_balances(accounts, wait=False):
    """
    :param accounts: An iterable of account names to be refunded.
    :param wait: If true, wait for a transaction to succeed before continuing.
    :return: A list of transaction hashes for all the refund transactions.
    """
    config = get_config()
    Loggers.general.info("Refunding accounts...")
    txn_hashes = []
    account_addresses = []
    for account in accounts:
        for shard_index in range(len(config['ENDPOINTS'])):
            amount = get_balances(account)[shard_index]["amount"]
            amount -= config["ESTIMATED_GAS_PER_TXN"]
            if amount > config['ESTIMATED_GAS_PER_TXN']:
                from_address = cli.get_address(account)
                to_address = config['REFUND_ACCOUNT']
                account_addresses.append(from_address)
                pw = get_fast_loaded_passphrase(account) if is_fast_loaded(account) else ''
                txn_hash = send_transaction(from_address, to_address, shard_index,
                                            shard_index, amount, pw=pw, wait=wait)
                txn_hashes.append({"shard": shard_index, "hash": txn_hash})
    Loggers.general.info(f"Refund transaction hashes: {txn_hashes}")
    return txn_hashes


def reset(safe=True):
    accounts_added = list(_accounts_added)
    return_balances(accounts_added, wait=safe)
    remove_accounts(accounts_added, backup=safe)
    account_balances.clear()
    _accounts_added.clear()
    _fast_loaded_accounts.clear()

