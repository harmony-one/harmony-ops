#!/usr/bin/env python3

import time
import sys
import logging
import datetime
from multiprocessing.pool import ThreadPool

import harmony_transaction_generator as tx_gen
from harmony_transaction_generator import account_manager
from harmony_transaction_generator import analysis
import pyhmy
from pyhmy import cli
from pyhmy import util

verbose = True

# TODO: improve tx_gen performance for more txns/sec.
# TODO: improve funding logic to make it more efficient.

tx_gen.set_config({
    "AMT_PER_TXN": [1e-9, 1e-9],
    "NUM_SRC_ACC": 1,
    "NUM_SNK_ACC": 1,
    "MAX_TXN_GEN_COUNT": None,
    "ONLY_CROSS_SHARD": False,
    "ESTIMATED_GAS_PER_TXN": 1e-3,
    "INIT_SRC_ACC_BAL_PER_SHARD": 1,
    "TXN_WAIT_TO_CONFIRM": 60,
    "MAX_THREAD_COUNT": 16,
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
    assert pyhmy.__version__.major == 20, "wrong pyhmy version, update please"
    assert pyhmy.__version__.minor > 0, "wrong pyhmy version, update please"
    env = cli.download("./bin/hmy_cli", replace=False)
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

    config = tx_gen.get_config()
    tx_gen.load_accounts("./localnet_validator_keys", "", fast_load=True)
    source_accounts = tx_gen.create_accounts(config["NUM_SRC_ACC"], "src_acc")
    sink_accounts = tx_gen.create_accounts(config["NUM_SNK_ACC"], "snk_acc")
    tx_gen.fund_accounts(source_accounts)

    tx_gen_pool = ThreadPool(processes=1)
    start_time = datetime.datetime.utcnow()  # MUST be utc
    tx_gen_pool.apply_async(lambda: tx_gen.start(source_accounts, sink_accounts))
    time.sleep(30)
    tx_gen.stop()
    end_time = datetime.datetime.utcnow()  # MUST be utc
    tx_gen.return_balances(source_accounts)
    tx_gen.return_balances(sink_accounts)
    tx_gen.remove_accounts(source_accounts)
    tx_gen.remove_accounts(sink_accounts)
    time.sleep(25)
    report = analysis.verify_transactions(tx_gen.Loggers.transaction.filename, start_time, end_time)
    print(report)

