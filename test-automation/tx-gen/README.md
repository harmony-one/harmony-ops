# Transaction Generator Python library

**This is for python 3.6+ only**

## Installation Requirements

1.) Check that the latest version of pyhmy (20.1.5) is installed. 
The pyhmy python library is used to interact with our blockchain. You can check your version of pyhmy with: `pip freeze | grep pyhmy`
 
> If your version is not updated or pyhmy is not listed, run:
>```
>python3 -m pip install pyhmy==20.1.5
>``` 

2.) Make sure you have a localnet running. 
Change the directory to the main repo (.../harmony-one/harmony) and run `./test/debug.sh` to start up a localnet.
> If you do not have the main repo cloned, go to https://github.com/harmony-one/harmony, clone the repo and 
follow the installation instructions. Then start the local net.   


## Installation

Clone this repo (https://github.com/Daniel-VDM/harmony-ops), change into the directory (.../harmony-ops/test-automation/tx-gen) and run:
```
make install
```

## Running the example
While in this directory (harmony-ops/test-automation/tx-gen), run:
```
python3 localnet_example.py
```

## Run example using other keys
There are keys to the run the localnet_example.py in the folder /localnet_validator_keys. 
To run the localnet_example.py using another set of keys (ex. the keys that were shared), here is an option:
1. Open the *localnet_example.py* file. Find the line `tx_gen.load_accounts("./localnet_validator_keys", "", fast_load=True)` 
and change `./localnet_validator_keys` to the directory of your keys, and the `""` to the passphrase for ALL keys.


## How it works
The documentation is in progress, but please look at the `localnet_example.py` for some idea of how it works.
Essentially, it follows a source / sink model for transaction generation, explained more in the `start` function
of `./harmony_transaction_generator/generator.py`

Look at the annotations for each key in the config file. These are modify these to perform testing.  

## Caveat
**The package has NOT been thoroughly tested so please report bugs and/or PR fixes if you find any, thank you!** 

## Troubleshooting Errors While Testing
####Possible fixes
* Backup and clear keystore at `~/.hmy_cli/account-keys`
* Update pyhmy to latest version.
* If `current balance is not enough for requested transfer`, 
try increasing the 'INIT_SRC_ACC_BAL_PER_SHARD' value in the config file


## TODO
* Documentation.
* More testing
* Verify reset logic for multiple runs.
* improve config verification to fail early.