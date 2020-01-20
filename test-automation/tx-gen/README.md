# Transaction Generator Python library

**This is for python 3.6+ only**

## Installation Requirements

Check that the latest version of pyhmy (20.1.8) is installed. 
The pyhmy python library is used to interact with our blockchain. You can check your version of pyhmy with: `pip freeze | grep pyhmy`
 
> If your version is not updated or pyhmy is not listed, run:
>```
>python3 -m pip install pyhmy==20.1.8
>``` 


## Installation

Clone this repo (https://github.com/Daniel-VDM/harmony-ops), change into the directory (.../harmony-ops/test-automation/tx-gen) and run:
```
make install
```

## Examples

Example script when running for devnet can be seen [here](https://gist.github.com/Daniel-VDM/220f6736ff9270bc9535d5df55be106d)

While in this directory (harmony-ops/test-automation/tx-gen), run:
```
python3 localnet_example.py
```
> *MAKE SURE TO HAVE A LOCALNET RUNNING*


## Important note about funding keys
One must have keys in the keystore that have funds on ALL shards (if one wishes to funds accounts on all shards).
Note that one account does NOT have to have funds on all shard, but across all accounts in the keystore, there should be funds on all shards
> This is because the library only does same shard transfers when funding. 


## How it works
A video demoing library can be seen [here](https://www.youtube.com/watch?v=rTp9wZn1EqE&feature=youtu.be)

The full documentation is in progress, but please look at the `localnet_example.py` for some idea of how it works.
Essentially, it follows a source / sink model for transaction generation (explained more in the `start` function
of `./harmony_transaction_generator/generator.py`). Moreover, the annotations of the config in `localnet_example.py`
should give a better idea of how to use the library.

## Analysis
The `analysis` module of this library has a `verify_transaction` function that looks at the transaction logs and checks
if said transactions appear on the blockchain. Refer to `./harmony_transaction_generator/analysis.py` for mode details
on how it works.

The library logs everything it can, so one can read the log files to analyze it. The filepath/filename can be accessed with
the `filename` attribute of the logger, for example `tx_gen.Loggers.transaction.filename`.
> Note that all times in the logs are in UTC.

## Caveat
**The package has NOT been thoroughly tested so please report bugs and/or PR fixes if you find any, thank you!** 

## Troubleshooting Errors While Testing
####Possible fixes
* Backup and clear keystore at `~/.hmy_cli/account-keys`
* Update pyhmy to latest version, can be checked [here](https://pypi.org/project/pyhmy/).
> Check version with `python3 -m pip list | grep pyhmy` 
* If `current balance is not enough for requested transfer`, try increasing the 'INIT_SRC_ACC_BAL_PER_SHARD' value in the config file


## TODO
* Implement transaction plan logic once CLI has this feature implemented. 
* Documentation.
* Verify reset logic for multiple runs.