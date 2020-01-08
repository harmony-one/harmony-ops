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


def set_config(input_config):
    assert isinstance(input_config, dict)
    # TODO: validate that config is correct.
    config.clear()
    config.update(input_config)
