import datetime
from pyhmy.logging import ControlledLogger

_config = {
    "AMT_PER_TXN": [1e-9, 1e-9],  # The random range for each transaction in the transaction-generation
    "NUM_SRC_ACC": 32,  # The number of possible source accounts for all transactions, higher = more tps
    "NUM_SNK_ACC": 1,  # The number of possible destination / sink accounts for all transaction
    "MAX_TXN_GEN_COUNT": None,  # The upper bound of the number generated transaction, regardless of if `stop` is called
    "ONLY_CROSS_SHARD": False,  # If true, forces source and destination shards to be different
    "ENFORCE_NONCE": False,  # If true, will only generate transactions with a valid nonce
    "ESTIMATED_GAS_PER_TXN": 1e-3,  # The estimated gas, hardcoded
    "INIT_SRC_ACC_BAL_PER_SHARD": 1,  # The initial balance for EVERY source account
    "TXN_WAIT_TO_CONFIRM": 60,  # The timeout when a transaction is sent (only used in setup related functions)
    "MAX_THREAD_COUNT": 16,  # Max thread is recommended to be less than your v-core count
    "ENDPOINTS": [  # Endpoints for all transaction, index i = shard i
        "https://api.s0.pga.hmny.io/",
        "https://api.s1.pga.hmny.io/",
        "https://api.s2.pga.hmny.io/"
    ],
    "SRC_SHARD_WEIGHTS": [  # Adjust the likelihood that shard i (i = index) gets chosen to be the source shard
        1,                  # Bigger number = higher likelihood of shard i begin chosen
        1,                  # 0 = 0% chance of being chosen
        1
    ],
    "SNK_SHARD_WEIGHTS": [  # Adjust the likelihood that shard i (i = index) gets chosen to be the source shard
        1,
        1,
        1
    ],
    "CHAIN_ID": "devnet",  # The chain id for all transaction, should be devnet if not localnet.
    "REFUND_ACCOUNT": "one1j9hwh7vqz94dsk06q4h9hznr4wlr3x5zup6wz3",  # All refunds will be sent to this address
}
import_account_name_prefix = "_tx_gen_"


class Loggers:
    """
    A collection of loggers for the transaction generator.
    """
    general = ControlledLogger(f"general_log_{datetime.datetime.utcnow()}", "./logs/general")
    transaction = ControlledLogger(f"transaction_log_{datetime.datetime.utcnow()}", "./logs/transaction")
    balance = ControlledLogger(f"balance_log_{datetime.datetime.utcnow()}", "./logs/balance")
    report = ControlledLogger(f"report_log_{datetime.datetime.utcnow()}", "./logs/report")


def start_new_loggers():
    """
    This reinitialize all loggers in `pdoc.Loggers`.
    Note that new files will be generated in the process.
    """
    start_new_general_logger()
    start_new_transaction_logger()
    start_new_balance_logger()
    start_new_report_logger()


def start_new_general_logger():
    """
    This reinitialize the general logger in `pdoc.Loggers`.
    Note that new files will be generated in the process.
    """
    Loggers.general = ControlledLogger(f"general_log_{datetime.datetime.utcnow()}", "./logs/general")


def start_new_transaction_logger():
    """
    This reinitialize the transaction logger in `pdoc.Loggers`.
    Note that new files will be generated in the process.
    """
    Loggers.transaction = ControlledLogger(f"transaction_log_{datetime.datetime.utcnow()}", "./logs/transaction")


def start_new_balance_logger():
    """
    This reinitialize the balance logger in `pdoc.Loggers`.
    Note that new files will be generated in the process.
    """
    Loggers.balance = ControlledLogger(f"balance_log_{datetime.datetime.utcnow()}", "./logs/balance")


def start_new_report_logger():
    """
    This reinitialize the report logger in `pdoc.Loggers`.
    Note that new files will be generated in the process.
    """
    Loggers.report = ControlledLogger(f"report_log_{datetime.datetime.utcnow()}", "./logs/report")


def write_all_logs():
    """
    Write all the logs in `pdoc.Loggers`
    """
    Loggers.general.write()
    Loggers.transaction.write()
    Loggers.balance.write()
    Loggers.report.write()


def _validate_config():
    assert isinstance(_config, dict)
    if not isinstance(_config["AMT_PER_TXN"], list) or len(_config["AMT_PER_TXN"]) != 2 \
            or _config["AMT_PER_TXN"][0] < 0:
        raise ValueError("Amount per transaction must be a range from 0")
    if not isinstance(_config["NUM_SRC_ACC"], int) or _config["NUM_SRC_ACC"] < 0:
        raise ValueError("Number of Source Accounts cannot be negative")
    if not isinstance(_config["NUM_SNK_ACC"], int) or _config["NUM_SNK_ACC"] < 0:
        raise ValueError("Number of Sink Accounts cannot be negative")
    # TODO: check max generation count: input_config["MAX_TXN_GEN_COUNT"]
    if not isinstance(_config["ONLY_CROSS_SHARD"], bool):
        raise ValueError("Only Cross Shard must be a boolean")
    if not isinstance(_config["ESTIMATED_GAS_PER_TXN"], (int, float)) or _config["ESTIMATED_GAS_PER_TXN"] < 0:
        raise ValueError("Estimated gas per transaction cannot be negative")
    if not isinstance(_config["INIT_SRC_ACC_BAL_PER_SHARD"], (int, float)) \
            or _config["INIT_SRC_ACC_BAL_PER_SHARD"] < 0:
        raise ValueError("Initial Source Account Balance per shard cannot be negative")
    if not isinstance(_config["TXN_WAIT_TO_CONFIRM"], (int, float)) or _config["TXN_WAIT_TO_CONFIRM"] < 0:
        raise ValueError("Transaction wait to confirm time cannot be negative")
    if _config["MAX_THREAD_COUNT"] is not None and not (isinstance(_config["MAX_THREAD_COUNT"], int)
                                                        and _config["MAX_THREAD_COUNT"] > 0):
        raise ValueError("Max Threads cannot be negative")
    num_shards = len(_config["ENDPOINTS"])
    # TODO: check endpoints are valid: input_config["ENDPOINTS"]
    if not isinstance(_config["SRC_SHARD_WEIGHTS"], list) or len(_config["SRC_SHARD_WEIGHTS"]) != num_shards:
        raise ValueError("Source Shard Weights must be list of len shards")
    if not isinstance(_config["SNK_SHARD_WEIGHTS"], list) or len(_config["SNK_SHARD_WEIGHTS"]) != num_shards:
        raise ValueError("Sink Shard Weights must be list of len shards")
    # TODO: check chain_ID: input_config["CHAIN_ID"]
    if not _config["REFUND_ACCOUNT"].startswith("one1"):
        raise ValueError("Refund account must be valid account")


def set_config(input_config):
    """
    Validate a config, `input_config`, and set the config for the transaction generator.
    """
    input_keys = input_config.keys()
    assert "ENDPOINTS" in input_keys, "Must specify endpoints"
    assert isinstance(input_config["ENDPOINTS"], list)
    if "SRC_SHARD_WEIGHTS" not in input_keys:
        input_config["SRC_SHARD_WEIGHTS"] = [1] * len(input_config["ENDPOINTS"])
    if "SNK_SHARD_WEIGHTS" not in input_keys:
        input_config["SNK_SHARD_WEIGHTS"] = [1] * len(input_config["ENDPOINTS"])
    _config.update(input_config)
    _validate_config()


def get_config():
    """
    :returns a COPY of the current config (to prevent accidental modification of config)
    """
    return _config.copy()
