# Test API script.

- Make sure newman (and by extention node.js) is installed, do `npm install -g newman` (https://www.npmjs.com/package/newman)
- Make sure that you are using python 3. 

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
               [--cli_path HMY_BINARY_PATH] [--keystore KEYS_DIR]

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
  --keystore KEYS_DIR   Direcotry of keystore to import. Must follow the
                        format of CLI's keystore. Default is
                        ./TestnetValidatorKeys
```

## Notes / Bugs
  - This script is known to work with the *included* `pyhmy` module. It may not work with newer versions.
  - The raw transaction used in this test is **always** a cross-shard transaction. 
  - There is a 25 second pause after the first test to ensure txn is on the blockchain.
  - `hmy_getCXReceptByHash` is known to fail because of unknown params.
  - `hmy_resendCx` will fail by extension of above.
  - `hmy_getFilterChanges` will fail because of unknown params. 

## TODO
  - Document how to add more tests using postman. 

