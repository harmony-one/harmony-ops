#
# At the very least, this package should include the binary of the harmony CLI.
# This package requires the pexpect module: https://pypi.org/project/pexpect/ .
#

from pyhmy.cli import HmyCLI, get_environment
import os

# Find the CLI binary for HmyCLI.
for root, dirs, files in os.walk(os.path.curdir):
    if "hmy" in files:
        HmyCLI.hmy_binary_path = os.path.join(root, "hmy").replace("./", "")
        break

# If needed, default the CLI binary for HmyCLI to the one included in this package.
if not HmyCLI.hmy_binary_path:
    this_file_path = os.path.realpath(__file__).replace("/__init__.py", "")
    default_hmy_path = f"{this_file_path}/hmy_default"
    assert os.path.isfile(default_hmy_path), "Default harmony CLI binary is not included in pyhmy module"
    HmyCLI.hmy_binary_path = default_hmy_path
