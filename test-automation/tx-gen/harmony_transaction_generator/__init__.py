import sys
import warnings

from .common import (
    Loggers,
    set_config,
    get_config,
    start_new_loggers,
    start_new_general_logger,
    start_new_transaction_logger,
    start_new_balance_logger,
    start_new_report_logger,
    write_all_logs
)
from .account_manager import (
    account_balances,
    get_balances,
    load_accounts,
    remove_accounts,
    send_transaction,
    return_balances,
    reset
)
from .fund import (
    fund_accounts
)
from .generator import (
    create_accounts,
    start,
    stop,
)

if sys.version_info.major < 3:
    warnings.simplefilter("always", DeprecationWarning)
    warnings.warn(
        DeprecationWarning(
            "`harmony-transaction-generator` does not support Python 2. Please use Python 3."
        )
    )
    warnings.resetwarnings()

if sys.platform.startswith('win32') or sys.platform.startswith('cygwin'):
    warnings.simplefilter("always", ImportWarning)
    warnings.warn(
        ImportWarning(
            "`harmony-transaction-generator` does not work on Windows or Cygwin."
        )
    )
    warnings.resetwarnings()
