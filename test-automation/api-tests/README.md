# Test API script.

Related internal [gitbook](https://app.gitbook.com/@harmony-one/s/onboarding-wiki/developers/api-test-automation)

- Make sure newman (and by extention node.js) is installed, do `npm install -g newman` (https://www.npmjs.com/package/newman)
- Make sure that you are using python 3.
- Make sure that you have `pyhmy` module for python3 [here](https://pypi.org/project/pyhmy/).
- Make sure that you have `requests` module for python3 [here](https://pypi.org/project/requests/).
- Make sure that you have `jq` installed.
- Make sure to have the CLI binary in this directory with the name `hmy` (or specifiy the binary path as an option).
- Make sure the CLI version is v132 or newer (that is commit `03621a931518dea582d4327671e0add33296a88d` or newer of *go-sdk*)

## Setup
The test will require at least 2 keys to accounts that have funds on the network that you are testing.
Make sure that the keystore follows the follow structure:
```
├── Keystore_Directory
│   ├── s0
│   │   └── one103q7qe5t2505lypvltkqtddaef5tzfxwsse4z7.key
│   └── s1
│       └── one1est2gxcvavmtnzc7mhd73gzadm3xxcv5zczdtw.key
```

## Running the test
Example command for testnet test (option default is for testnet).
```bash
python3 test.py --delay=30
```

Example command for localnet test (no explorer tests):
```bash
python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" --rpc_endpoint_dst="http://localhost:9501/" --keystore=./LocalnetValidatorKeys/ --chain_id="localnet"
```

Example command for (testnet) no-explorer no staking test
```bash
python3 test.py --test_dir=./tests/no-explorer/ --keystore=<TestnetValidatorKeys_DIR> --ignore_staking_test
```

Example command for (testnet) explorer only test:
```bash
python3 test.py --test_dir=./tests/only-explorer/ --keystore=<TestnetValidatorKeys_DIR>
```

Example command for mainnet test (no explorer tests):
```bash
python3 test.py --rpc_endpoint_src=https://api.s0.t.hmny.io/ --rpc_endpoint_dst=https://api.s1.t.hmny.io/ --exp_endpoint=http://e0.t.hmny.io:5000/ --chain_id=mainnet --keystore=./MainnetKeys/ --test_dir=./tests/no-explorer/
```

## Options
There are some options for the python script, here is the output of the help message:
```
usage: test.py [-h] [--test_dir TEST_DIR] [--iterations ITERATIONS]
               [--start_epoch START_EPOCH]
               [--rpc_endpoint_src HMY_ENDPOINT_SRC]
               [--rpc_endpoint_dst HMY_ENDPOINT_DST] [--src_shard SRC_SHARD]
               [--dst_shard DST_SHARD] [--exp_endpoint HMY_EXP_ENDPOINT]
               [--delay TXN_DELAY] [--chain_id CHAIN_ID]
               [--cli_path HMY_BINARY_PATH] [--cli_passphrase PASSPHRASE]
               [--keystore KEYS_DIR] [--ignore_regression_test]
               [--ignore_staking_test]

Wrapper python script to test API using newman.

optional arguments:
  -h, --help            show this help message and exit
  --test_dir TEST_DIR   Path to test directory. Default is './tests/default'
  --iterations ITERATIONS
                        Number of attempts for a successful test. Default is
                        5.
  --start_epoch START_EPOCH
                        The minimum epoch before starting tests. Default is 1.
  --rpc_endpoint_src HMY_ENDPOINT_SRC
                        Source endpoint for Cx. Default is
                        https://api.s0.b.hmny.io/
  --rpc_endpoint_dst HMY_ENDPOINT_DST
                        Destination endpoint for Cx. Default is
                        https://api.s1.b.hmny.io/
  --src_shard SRC_SHARD
                        The source shard of the Cx. Default assumes associated
                        shard from src endpoint.
  --dst_shard DST_SHARD
                        The destination shard of the Cx. Default assumes
                        associated shard from dst endpoint.
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
                        Passphrase used to unlock the keystore. Default is ''
  --keystore KEYS_DIR   Directory of keystore to import. Must follow the
                        format of CLI's keystore. Default is
                        ./TestnetValidatorKeys
  --ignore_regression_test
                        Disable the regression tests.
  --ignore_staking_test
                        Disable the staking tests.
```

## Notes
  - If no source or destination shard is provided, the script will infer the respective shard from the source and destination endpoints (given that it is a known format -- reference code for details).
  - The chain_id option can be set to localnet if one needs to run the tests on localnet. This is just a creature comfort as the localnet uses the testnet chain ID
  - The raw transaction used in this test is **always** a cross-shard transaction.
  - It is recommended to wait around 30 seconds for a Cx to finalize.
  - Each iteration will try the tests **on the same raw transaction**.
  - **If you get that you cannot decrypt the keystore (and you are sure that the passphrase is correct), go to the CLI's keystore at `~/.hmy_cli/account-keys` and delete the files that start with `_Test_key_`.**

## Bugs
  - Staking tests do **not** currently work, add the option --ignore_staking_test to ignore those tests.
  - `hmy_getFilterChanges` is not being tested because of unknown params.
  - `hmy_getLogs` is not being tested because of unknown params.

## Adding tests
  - To run your own collection (or an updated version of the collection above) export the collection, global variables, and environment variables to `<test_dir>/test.json`, `<test_dir>/global.json`, and `<test_dir>/env.json` respectively. For more details on how to export a test, reference [here](https://kb.datamotion.com/?ht_kb=postman-instructions-for-exporting-and-importing#how-to-export-a-collection-from-postman). For more details on how to export global variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_globals/). For more details on how to export environment variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_environments/)


# JS Tests

## Running Tests

Make sure your Harmony localNet environment is running and then try the following command.

```
RPC_SRC="http://localhost:9500" node test.js
```