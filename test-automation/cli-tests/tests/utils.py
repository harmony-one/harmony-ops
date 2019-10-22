import inspect
import logging
import datetime


class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


def get_logger(filename):
    logging.basicConfig(filename=f"{filename}", filemode='a', format="%(message)s")
    logging.warning(f"[{datetime.datetime.now()}] {'=' * 10}")

    def log(message, error=True):
        func = inspect.currentframe().f_back.f_code
        final_msg = "(%s:%i) %s" % (
            func.co_name,
            func.co_firstlineno,
            message
        )
        if error:
            logging.warning(final_msg)
            print(f"[ERROR] {final_msg}")
        else:
            print(final_msg)

    return log


def test_announce(fn):
    def warp(*args):
        print(f"Testing {Colors.WARNING}{fn.__name__}{Colors.ENDC}")
        return fn(*args)
    return warp
