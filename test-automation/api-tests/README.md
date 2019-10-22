# Test API script.

Related internal [gitbook](https://app.gitbook.com/@harmony-one/s/onboarding-wiki/developers/api-test-automation)

- Make sure newman (and by extention node.js) is installed, do `npm install -g newman` (https://www.npmjs.com/package/newman)
- Make sure that you are using python 3. 
- Make sure that you have `pexpect` module for python (https://pypi.org/project/pexpect/). 
- Make sure that you have `jq` installed.
- Make sure to have the CLI binary in this directory with the name `hmy` (or specifiy the binary path as an option).
- Make sure the CLI version is v105 or newer (that is commit `1f25a418001488044f78cbfbac31d9bf06b1f995` or newer of *go-sdk*)

## Setup
The test will require at least 2 keys to accounts that have funds on the network that you are testing. 
There are 2 keystore directories included here, `LocalnetValidatorKeys` and `TestnetValidatorKeys`, which should suffice for their respective networks. Note that the keystore must follow the keystore structure used with the CLI (reference the 2 included keystore for an example). 

## Running the test
Example command for testnet test (option default is for testnet).
```bash
python3 test.py --delay=45
```

Example command for localnet test (no explorer tests):
```bash
python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" --rpc_endpoint_dst="http://localhost:9501/" --keystore=./LocalnetValidatorKeys/ --chain_id="localnet"
```

Example command for explorer only test:
```bash
python3 test.py --test_dir=./tests/only-explorer/
```

## Options
There are some options for the python script, here is the output of the help message:
```
usage: test.py [-h] [--test_dir TEST_DIR] [--iterations ITERATIONS]
               [--rpc_endpoint_src HMY_ENDPOINT_SRC]
               [--rpc_endpoint_dst HMY_ENDPOINT_DST]
               [--exp_endpoint HMY_EXP_ENDPOINT] [--delay TXN_DELAY]
               [--chain_id CHAIN_ID] [--cli_path HMY_BINARY_PATH]
               [--cli_passphrase PASSPHRASE] [--keystore KEYS_DIR]

Wrapper python script to test API using newman.

optional arguments:
  -h, --help            show this help message and exit
  --test_dir TEST_DIR   Path to test directory. Default is './tests/default'
  --iterations ITERATIONS
                        Number of attempts for a successful test. Default is
                        5.
  --rpc_endpoint_src HMY_ENDPOINT_SRC
                        Source endpoint for Cx. Default is
                        https://api.s0.b.hmny.io/
  --rpc_endpoint_dst HMY_ENDPOINT_DST
                        Destination endpoint for Cx. Default is
                        https://api.s1.b.hmny.io/
  --exp_endpoint HMY_EXP_ENDPOINT
                        Default is http://e0.b.hmny.io:5000/
  --delay TXN_DELAY     The time to wait before checking if a Cx/Tx is on the
                        blockchain. Default is 30 seconds. (Input is in
                        seconds)
  --chain_id CHAIN_ID   Chain ID for the CLI. Default is 'testnet'
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
  - This script makes the assumption that there are only 2 shard and will only send a cross shard transactions between shard 0 and shard 1. 
  - The raw transaction used in this test is **always** a cross-shard transaction. 
  - It is recommended to wait around 30 seconds for a Cx to finalize. By default, this test waits 30 seconds.
  - For a new test, make sure the test directory looks like `./tests/default` (including file names).

## Bugs
  - `hmy_getFilterChanges` is not being tested because of unknown params.
  - `hmy_getLogs` is not being tested because of unknown params. 
  - Some Cx and/or Tx related tests will fail on a localnet because endpoint of shard 1 is unknown.

## Adding tests
  - The tests ran are from the postman collection [here](https://harmony.postman.co/collections/8725027-fb1d4862-2f24-447f-9ea5-6ba28f513cd3?version=latest&workspace=4f2f1b50-78d3-43c5-8070-5c563fd22e3b). Shareable link [here](https://www.getpostman.com/collections/84d637d678e14229562d).
  - To run your own collection (or an updated version of the collection above) export the collection, global variables, and environment variables to `tests/test.json`, `tests/global.json`, and `tests/env.json` respectively. For more details on how to export a test, reference [here](https://kb.datamotion.com/?ht_kb=postman-instructions-for-exporting-and-importing#how-to-export-a-collection-from-postman). For more details on how to export global variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_globals/). For more details on how to export environment variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_environments/)
