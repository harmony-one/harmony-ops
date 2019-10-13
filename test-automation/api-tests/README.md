# Test API script.

- Make sure newman (and by extention node.js) is installed, do `npm install -g newman` (https://www.npmjs.com/package/newman)
- Make sure that you are using python 3. 
- Make sure that you have `pexpect` module for python (https://pypi.org/project/pexpect/). 
- Make sure to have the CLI binary in this directory with the name `hmy` (or specifiy the binary path as an option).

## Setup
This test will require at least 2 keys to accounts that have some funds (for sending a transaction).
Included in `./TestnetValidatorKeys` are keys to validators and should suffice for this test.

## Running the test
Simply run the python script. Ex:
```
python3 test.py
```

## Options
There are some options for the python script, here is the output of the help message:
```
usage: test.py [-h] [--rpc_endpoint HMY_ENDPOINT]
               [--exp_endpoint HMY_EXP_ENDPOINT] [--chain-id CHAIN_ID]
               [--cli_path HMY_BINARY_PATH] [--cli_passphrase PASSPHRASE]
               [--keystore KEYS_DIR]

Wrapper python script to test API using newman.

optional arguments:
  -h, --help            show this help message and exit
  --rpc_endpoint HMY_ENDPOINT
                        Default is https://api.s0.b.hmny.io/
  --exp_endpoint HMY_EXP_ENDPOINT
                        Default is http://e0.b.hmny.io:5000/
  --chain-id CHAIN_ID   Chain ID for the CLI. Default is 'testnet'
  --cli_path HMY_BINARY_PATH
                        ABSOLUTE PATH of CLI binary. Default uses the CLI
                        included in pyhmy module
  --cli_passphrase PASSPHRASE
                        Passphrase used to unlock the keystore. Default is
                        'harmony-one'
  --keystore KEYS_DIR   Direcotry of keystore to import. Must follow the
                        format of CLI's keystore. Default is
                        ./TestnetValidatorKeys
```

## Notes
  - This script is known to work with the hmy CLI as of commit `1f25a418001488044f78cbfbac31d9bf06b1f995`.
  - The tests ran are from the postman collection [here](https://harmony.postman.co/collections/8474019-7232849f-cafd-4385-96b5-67513f9e37d3?version=latest&workspace=4f2f1b50-78d3-43c5-8070-5c563fd22e3b)
  - The raw transaction used in this test is **always** a cross-shard transaction. 
  - There is a 25 second pause after the first test to ensure txn is on the blockchain.

## Bugs
  - `hmy_getCXReceptByHash` is known to fail because of unknown params.
  - `hmy_resendCx` will fail by extension of above.
  - `hmy_getFilterChanges` will fail because of unknown params. 

## TODO
  - Document how to add more tests using postman. 

