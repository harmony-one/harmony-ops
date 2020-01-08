import datetime
from pyhmy.logging import ControlledLogger

config = {}
import_account_name_prefix = "_Benchmark_"


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


def _validate_config(input_config):
    assert isinstance(input_config, dict)
    if not isinstance(input_config["AMT_PER_TXN"], list) or len(input_config["AMT_PER_TXN"]) != 2 \
            or input_config["AMT_PER_TXN"][0] < 0:
        raise ValueError("Amount per transaction must be a range from 0")
    if not isinstance(input_config["NUM_SRC_ACC"], int) or input_config["NUM_SRC_ACC"] < 0:
        raise ValueError("Number of Source Accounts cannot be negative")
    if not isinstance(input_config["NUM_SNK_ACC"], int) or input_config["NUM_SNK_ACC"] < 0:
        raise ValueError("Number of Sink Accounts cannot be negative")
    # TODO: check max generation count: input_config["MAX_TXN_GEN_COUNT"]
    if not isinstance(input_config["ONLY_CROSS_SHARD"], bool):
        raise ValueError("Only Cross Shard must be a boolean")
    if not isinstance(input_config["ESTIMATED_GAS_PER_TXN"], (int, float)) or input_config["ESTIMATED_GAS_PER_TXN"] < 0:
        raise ValueError("Estimated gas per transaction cannot be negative")
    if not isinstance(input_config["INIT_SRC_ACC_BAL_PER_SHARD"], (int, float)) \
            or input_config["INIT_SRC_ACC_BAL_PER_SHARD"] < 0:
        raise ValueError("Initial Source Account Balance per shard cannot be negative")
    if not isinstance(input_config["TXN_WAIT_TO_CONFIRM"], (int, float)) or input_config["TXN_WAIT_TO_CONFIRM"] < 0:
        raise ValueError("Transaction wait to confirm time cannot be negative")
    if not isinstance(input_config["MAX_THREAD_COUNT"], int) or input_config["MAX_THREAD_COUNT"] < 0:
        raise ValueError("Max Threads cannot be negative")
    num_shards = len(input_config["ENDPOINTS"])
    # TODO: check endpoints are valid: input_config["ENDPOINTS"]
    if not isinstance(input_config["SRC_SHARD_WEIGHTS"], list) or len(input_config["SRC_SHARD_WEIGHTS"]) != num_shards:
        raise ValueError("Source Shard Weights must be list of len shards")
    if not isinstance(input_config["SNK_SHARD_WEIGHTS"], list) or len(input_config["SNK_SHARD_WEIGHTS"]) != num_shards:
        raise ValueError("Sink Shard Weights must be list of len shards")
    # TODO: check chain_ID: input_config["CHAIN_ID"]
    if not input_config["REFUND_ACCOUNT"].startswith("one1"):
        raise ValueError("Refund account must be valid account")
    if not isinstance(input_config["REFUND_ACCOUNT_PASSPHRASE"], str):
        raise ValueError("Refund Account Passphrase must be a string")


def set_config(input_config):
    _validate_config(input_config)
    config.clear()
    config.update(input_config)
