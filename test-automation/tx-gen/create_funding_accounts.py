"""
Example of how to fund accounts quickly using parts of the transaction generation.

Note that we need to place the faucet account's key in a directory similar to `./localnet_validator_key`
"""

import logging
import sys
import argparse
import multiprocessing
import time
from multiprocessing.pool import ThreadPool

import pyhmy
from pyhmy import cli
import harmony_transaction_generator as tx_gen


def parse_args():
    parser = argparse.ArgumentParser(description='Wrapper python script to test API using newman.')
    parser.add_argument("--count", dest="count", default=multiprocessing.cpu_count(),
                        help="Number of accounts to generate and fund", type=int)
    parser.add_argument("--faucet_key_dir", dest="faucet_key_dir", default="./faucet_key",
                        help="Number of accounts to generate and fund", type=str)
    parser.add_argument("--faucet_key_pw", dest="faucet_key_pw", default="",
                        help="Number of accounts to generate and fund", type=str)
    return parser.parse_args()


def setup():
    assert hasattr(pyhmy, "__version__")
    assert pyhmy.__version__.major == 20
    assert pyhmy.__version__.minor > 0
    env = cli.download("./bin/hmy_cli", replace=False)
    cli.environment.update(env)
    cli.set_binary("./bin/hmy_cli")


def log_writer(interval):
    while True:
        tx_gen.write_all_logs()
        time.sleep(interval)


if __name__ == "__main__":
    args = parse_args()
    setup()
    tx_gen.set_config({
        "AMT_PER_TXN": [1e-9, 1e-9],  # Not used
        "NUM_SRC_ACC": args.count,
        "NUM_SNK_ACC": 1,  # Not used
        "MAX_TXN_GEN_COUNT": None,  # Not used
        "ONLY_CROSS_SHARD": False,  # Not used
        "ESTIMATED_GAS_PER_TXN": 1e-3,
        "INIT_SRC_ACC_BAL_PER_SHARD": 1000,
        "TXN_WAIT_TO_CONFIRM": 60,
        "MAX_THREAD_COUNT": 16,
        "ENDPOINTS": [
            "https://api.s0.pga.hmny.io/",
            "https://api.s1.pga.hmny.io/",
            "https://api.s2.pga.hmny.io/"
        ],
        "SRC_SHARD_WEIGHTS": [
            1,
            1,
            1
        ],
        "SNK_SHARD_WEIGHTS": [
            1,
            1,
            1
        ],
        "CHAIN_ID": "devnet",
        "REFUND_ACCOUNT": "one1j9hwh7vqz94dsk06q4h9hznr4wlr3x5zup6wz3",  # Needs to be in keystore
        "REFUND_ACCOUNT_PASSPHRASE": ""
    })

    # Prints what is being logged.
    tx_gen.Loggers.general.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.balance.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.transaction.logger.addHandler(logging.StreamHandler(sys.stdout))
    tx_gen.Loggers.report.logger.addHandler(logging.StreamHandler(sys.stdout))

    log_writer_pool = ThreadPool(processes=1)
    log_writer_pool.apply_async(log_writer, (5,))

    tx_gen.load_accounts(args.faucet_key_dir, args.faucet_key_pw)
    accounts = tx_gen.create_accounts(args.count, "NEW_FUNDED_ACC")
    tx_gen.fund_accounts(accounts)  # Funds all the accounts with 1000 $one.
    print(f"Keystore path: {cli.get_account_keystore_path()}")
    print(f"Accounts added: {accounts}")
