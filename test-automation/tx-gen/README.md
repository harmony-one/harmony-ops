# Transaction Generator Python library

**This is for python 3.6+ only**

## Installation

Clone this repo, change into this directory and run:
```
make install
```

> You might need pyhmy (a python library for interacting with our blockchain). This can be installed with the following
command `python3 -m pip install pyhmy==20.1.3`. If you have it, you might need to update to at least
that version.

## Running the example
Make sure that you have a localnet running by running `./test/debug.sh` in the main repo. Then execute the following
command:

```
python3 localnet_example.py
```

## How it works
The documentation is in progress, but please look at the `localnet_example.py` for some idea of how it works.
Essentially, it follows a source / sink model for transaction generation.

## Caveat
**The package has NOT been thoroughly tested so please report bugs and/or PR fixes if you find any, thank you!** 

## TODO
* Documentation.
* More testing
* Verify reset logic for multiple runs.
* improve config verification to fail early.
* improve tx_gen performance for more txns/sec.
* improve funding logic to make it more efficient.