#!/usr/bin/env python3

import time
import sys
import logging
from multiprocessing.pool import ThreadPool

import transaction_generator as tx_gen
from transaction_generator import analysis
import pyhmy
from pyhmy import cli

verbose = True

tx_gen.set_config({
    "AMT_PER_TXN": 1e-9,
    "NUM_SRC_ACC": 5,
    "NUM_SNK_ACC": 1,
    "ONLY_CROSS_SHARD": True,
    "ESTIMATED_GAS_PER_TXN": 1e-3,
    "INIT_SRC_ACC_BAL_PER_SHARD": 1,
    "TXN_WAIT_TO_CONFIRM": 60,
    "MAX_THREAD_COUNT": 16,
    "SHARD_COUNT": 2,
    "ENDPOINTS": [
        "http://localhost:9500/",
        "http://localhost:9501/"
    ],
    "SRC_SHARD_WEIGHTS": [
        1,
        1
    ],
    "SNK_SHARD_WEIGHTS": [
        1,
        1
    ],
    "CHAIN_ID": "testnet",
    "REFUND_ACCOUNT": "one1j9hwh7vqz94dsk06q4h9hznr4wlr3x5zup6wz3",
    "REFUND_ACCOUNT_PASSPHRASE": ""
})


def setup():
    assert hasattr(pyhmy, "__version__")
    assert pyhmy.__version__.major == 20
    assert pyhmy.__version__.minor > 0
    env = cli.download("./bin/hmy_cli")
    cli.environment.update(env)
    cli.set_binary("./bin/hmy_cli")


def log_writer(interval):
    while True:
        tx_gen.write_all_logs()
        time.sleep(interval)


if __name__ == "__main__":
    setup()
    if verbose:
        tx_gen.Loggers.general.logger.addHandler(logging.StreamHandler(sys.stdout))
        tx_gen.Loggers.balance.logger.addHandler(logging.StreamHandler(sys.stdout))
        tx_gen.Loggers.transaction.logger.addHandler(logging.StreamHandler(sys.stdout))
        tx_gen.Loggers.report.logger.addHandler(logging.StreamHandler(sys.stdout))

    log_writer_pool = ThreadPool(processes=1)
    log_writer_pool.apply_async(log_writer, (5,))

    config = tx_gen.config
    tx_gen.load_accounts("./localnet_validator_keys", "", fast_load=True)
    source_accounts = tx_gen.create_accounts(config["NUM_SRC_ACC"], "src_acc")
    sink_accounts = tx_gen.create_accounts(config["NUM_SNK_ACC"], "snk_acc")
    tx_gen.fund_accounts(source_accounts)

    tx_gen_pool = ThreadPool(processes=1)
    tx_gen_pool.apply_async(lambda: tx_gen.start(source_accounts, sink_accounts))

    # TODO: test analysis.
    # TODO: add config verification.
    # TODO: improve tx_gen performance for more txns/sec.
    # TODO: improve funding logic to make it more efficient.
    # TODO: add examples for scenarios.

    time.sleep(30)
    tx_gen.stop()
    tx_gen.return_balances(source_accounts)
    tx_gen.return_balances(sink_accounts)
    tx_gen.remove_accounts(source_accounts)
    tx_gen.remove_accounts(sink_accounts)
