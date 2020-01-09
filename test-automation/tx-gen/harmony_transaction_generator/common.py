import datetime
from pyhmy.logging import ControlledLogger

_config = {}
import_account_name_prefix = "_tx_gen_"


class Loggers:
    general = ControlledLogger(f"general_log_{datetime.datetime.utcnow()}", "./logs/general")
    transaction = ControlledLogger(f"transaction_log_{datetime.datetime.utcnow()}", "./logs/transaction")
    balance = ControlledLogger(f"balance_log_{datetime.datetime.utcnow()}", "./logs/balance")
    report = ControlledLogger(f"report_log_{datetime.datetime.utcnow()}", "./logs/report")


def start_new_loggers():
    start_new_general_logger()
    start_new_transaction_logger()
    start_new_balance_logger()
    start_new_report_logger()


def start_new_general_logger():
    Loggers.general = ControlledLogger(f"general_log_{datetime.datetime.utcnow()}", "./logs/general")


def start_new_transaction_logger():
    Loggers.transaction = ControlledLogger(f"transaction_log_{datetime.datetime.utcnow()}", "./logs/transaction")


def start_new_balance_logger():
    Loggers.balance = ControlledLogger(f"balance_log_{datetime.datetime.utcnow()}", "./logs/balance")


def start_new_report_logger():
    Loggers.report = ControlledLogger(f"report_log_{datetime.datetime.utcnow()}", "./logs/report")


def write_all_logs():
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
    if not isinstance(_config["MAX_THREAD_COUNT"], int) or _config["MAX_THREAD_COUNT"] < 0:
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
    _config.clear()
    _config.update(input_config)
    _validate_config()


def get_config():
    """
    Has to return a copy to prevent accidental modifications of config
    """
    return _config.copy()
