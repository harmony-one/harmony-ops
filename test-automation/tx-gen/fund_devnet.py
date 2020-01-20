"""
A simple script ot fund all accounts for P-OPS and internal accounts.

Note: It assumes the devnet faucet keyfile is in `./devnet_faucet_key` and has an empty string as the passphrase.

To run, execute the following in the terminal:
```
python3 fund_devnet.py
```

After that you will get:
3 directories:
    - Private key directory containing all the key files for 'mini' faucets (15 keys).
    - P-ops key directory containing all the key files for p-ops (270 keys).
    - Internal key directory containing all the key files for internal usages (20 keys).
3 txt files:
    - Private key text file containing all the addresses and private keys for 'mini' faucets (15 keys).
    - P-ops key text file containing all the addresses and private keys for p-ops (270 keys).
    - Internal key directory containing all the addresses and private keys for internal usage (20 keys).
"""

import logging
import sys
import time
import os
import shutil
from multiprocessing.pool import ThreadPool

import pyhmy
from pyhmy import cli
import harmony_transaction_generator as tx_gen

private_keys_dir = "./private_faucet_keys"
pops_keys_dir = "./pops_faucet_keys"
internal_keys_dir = "./internal_faucet_keys"


def setup():
    assert hasattr(pyhmy, "__version__")
    assert pyhmy.__version__.major == 20, "wrong pyhmy version"
    assert pyhmy.__version__.minor == 1, "wrong pyhmy version"
    assert pyhmy.__version__.micro >= 8, "wrong pyhmy version, update please"
    env = cli.download("./bin/hmy", replace=False)
    cli.environment.update(env)
    cli.set_binary("./bin/hmy")
    if os.path.exists(private_keys_dir):
        shutil.rmtree(private_keys_dir)
        os.makedirs(private_keys_dir)
    if os.path.exists(pops_keys_dir):
        shutil.rmtree(pops_keys_dir)
        os.makedirs(pops_keys_dir)
    if os.path.exists(internal_keys_dir):
        shutil.rmtree(internal_keys_dir)
        os.makedirs(internal_keys_dir)


def log_writer(interval):
    while True:
        tx_gen.write_all_logs()
        time.sleep(interval)


def export_private_key(name):
    return cli.single_call(f"hmy keys export-private-key {cli.get_address(name)}")


if __name__ == "__main__":
    setup()
    tx_gen.set_config({
        "ESTIMATED_GAS_PER_TXN": 1e-3,
        "INIT_SRC_ACC_BAL_PER_SHARD": 5000000,
        "TXN_WAIT_TO_CONFIRM": 75,
        "MAX_THREAD_COUNT": None,
        "ENDPOINTS": [
            "https://api.s0.pga.hmny.io/",
            "https://api.s1.pga.hmny.io/",
            "https://api.s2.pga.hmny.io/"
        ],
        "CHAIN_ID": "devnet"
    })

    key_store_path = cli.get_account_keystore_path()

    # Prints what is being logged.
    tx_gen.Loggers.general.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.balance.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.transaction.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.report.logger.addHandler(logging.StreamHandler(sys.stdout))

    log_writer_pool = ThreadPool(processes=1)
    log_writer_pool.apply_async(log_writer, (5,))

    # === Generate private funding keys ===
    print("Bootstrapping funding process using faucet key in `./devnet_faucet_key`")
    tx_gen.load_accounts("./devnet_faucet_key", "")
    private_faucet_keys = tx_gen.create_accounts(15, "PRIVATE_FAUCET")
    tx_gen.fund_accounts(private_faucet_keys)
    for key_dir in os.listdir(key_store_path):
        if "PRIVATE_FAUCET" in key_dir:
            shutil.copytree(os.path.join(key_store_path, key_dir), f"{private_keys_dir}/{key_dir}")
    with open("private_faucet_keys.txt", 'w') as f:
        for n in private_faucet_keys:
            f.write(str((cli.get_address(n), export_private_key(n).strip())) + "\n")

    # === Generate p-ops keys ===
    print("Funding p-ops keys...")
    tx_gen.set_config({
        "ESTIMATED_GAS_PER_TXN": 1e-3,
        "INIT_SRC_ACC_BAL_PER_SHARD": 5000,
        "TXN_WAIT_TO_CONFIRM": 75,
        "MAX_THREAD_COUNT": None,
        "ENDPOINTS": [
            "https://api.s0.pga.hmny.io/",
            "https://api.s1.pga.hmny.io/",
            "https://api.s2.pga.hmny.io/"
        ],
        "CHAIN_ID": "devnet"
    })
    pops_faucet_keys = tx_gen.create_accounts(270, "POPS_FAUCET")
    tx_gen.fund_accounts(pops_faucet_keys)
    for key_dir in os.listdir(key_store_path):
        if "POPS_FAUCET" in key_dir:
            shutil.copytree(os.path.join(key_store_path, key_dir), f"{pops_keys_dir}/{key_dir}")
    with open("pops_faucet_keys.txt", 'w') as f:
        for n in pops_faucet_keys:
            f.write(str((cli.get_address(n), export_private_key(n).strip())) + "\n")
    tx_gen.remove_accounts(pops_faucet_keys, backup=False)  # Remove so that they don't get used as funding accounts

    # === Generate internal keys ===
    print("Funding internal keys...")
    tx_gen.set_config({
        "ESTIMATED_GAS_PER_TXN": 1e-3,
        "INIT_SRC_ACC_BAL_PER_SHARD": 100000,
        "TXN_WAIT_TO_CONFIRM": 75,
        "MAX_THREAD_COUNT": None,
        "ENDPOINTS": [
            "https://api.s0.pga.hmny.io/",
            "https://api.s1.pga.hmny.io/",
            "https://api.s2.pga.hmny.io/"
        ],
        "CHAIN_ID": "devnet"
    })
    internal_faucet_keys = tx_gen.create_accounts(20, "INTERNAL_FAUCET")
    tx_gen.fund_accounts(internal_faucet_keys)
    for key_dir in os.listdir(key_store_path):
        if "INTERNAL_FAUCET" in key_dir:
            shutil.copytree(os.path.join(key_store_path, key_dir), f"{internal_keys_dir}/{key_dir}")
    with open("internal_faucet_keys.txt", 'w') as f:
        for n in internal_faucet_keys:
            f.write(str((cli.get_address(n), export_private_key(n).strip())) + "\n")
    print("Finished funding...")
