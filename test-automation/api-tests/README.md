# API test script

Related internal [gitbook](https://app.gitbook.com/@harmony-one/s/onboarding-wiki/developers/api-test-automation)

- Make sure that you have set-up the development environment for the main harmony repo. If not, follow the main repo's README [here](https://github.com/harmony-one/harmony/blob/master/README.md).
- Make sure newman (and by extension node.js) is installed, do `npm install -g newman` (https://www.npmjs.com/package/newman)
- Make sure that you are using python 3.
- Make sure that you have `pyhmy` module for python3 [here](https://pypi.org/project/pyhmy/). You can install it with the following command `python3 -m install pyhmy`.
- Make sure that you have `requests` module for python3 [here](https://pypi.org/project/requests/). You can install it with the following command `python3 -m install requests`.
- Make sure that you have `jq` installed.
- Make sure to have the CLI binary in this directory with the name `hmy` or specify the binary path as an option.
- Make sure the CLI version is v185-1b8eae8 or newer (can be checked with `./hmy version`). Note that this may require [building the latest](https://docs.harmony.one/home/command-line-interface/using-the-harmony-cli-tool/download-and-installation#compiling-from-source) CLI from the go-sdk repo.

## Setup
**MAKE SURE YOU HAVE ALL OF THE DEPENDENCIES MENTIONED ABOVE**

The test will require at least 2 keys to accounts that have funds on the network that you are testing.
Make sure that the keystore follows the follow structure:
```
├── Keystore_Directory
│   ├── s0
│   │   └── one103q7qe5t2505lypvltkqtddaef5tzfxwsse4z7.key
│   └── s1
│       └── one1est2gxcvavmtnzc7mhd73gzadm3xxcv5zczdtw.key
```
> The included `LocalnetValidatorKeys` directory should suffice for localnet testing.

## Running the test
For localnet, one can just execute the `localnet_test.sh` script to run all of the tests. Note that this script
is what the main repo's Jenkins PR job uses to run the tests. 
```bash
chmod +x ./localnet_test.sh
./localnet_test.sh -w 60 -d 20 -i 5
```
> The `-w` option specifies the wait time (after the localnet has booted) before running the test.
> The `-d` option specifies the wait time between sending a transaction (Cx or Tx) and checking it.
> The `-i` option specifies the max number of attempts for the regression test (this should be left to default).

Example command for testnet test (option default is for testnet).
```bash
python3 test.py --delay=30
```

Example command for localnet test (no explorer tests):
```bash
python3 test.py --test_dir=./tests/no-explorer/ --rpc_endpoint_src="http://localhost:9500/" --rpc_endpoint_dst="http://localhost:9501/" --keystore=./LocalnetValidatorKeys/ --chain_id="testnet"
```

Example command for testnet (no-explorer & no staking test)
```bash
python3 test.py --test_dir=./tests/no-explorer/ --keystore=<TestnetValidatorKeys_DIR> --ignore_staking_test
```

Example command for testnet (explorer only test):
```bash
python3 test.py --test_dir=./tests/only-explorer/ --keystore=<TestnetValidatorKeys_DIR>
```

Example command for mainnet test (no explorer tests):
```bash
python3 test.py --rpc_endpoint_src=https://api.s0.t.hmny.io/ --rpc_endpoint_dst=https://api.s1.t.hmny.io/ --exp_endpoint=http://e0.t.hmny.io:5000/ --chain_id=mainnet --keystore=./MainnetKeys/ --test_dir=./tests/no-explorer/
```

## Options
Similar to the CLI, a bunch of settings can be set with options. Below is the help message for reference.
```
usage: test.py [-h] [--test_dir TEST_DIR] [--iterations ITERATIONS]
               [--start_epoch START_EPOCH] [--rpc_endpoint_src ENDPOINT_SRC]
               [--rpc_endpoint_dst ENDPOINT_DST] [--src_shard SRC_SHARD]
               [--dst_shard DST_SHARD] [--exp_endpoint ENDPOINT_EXP]
               [--delay TXN_DELAY] [--chain_id CHAIN_ID]
               [--cli_path HMY_BINARY_PATH] [--cli_passphrase PASSPHRASE]
               [--keystore KEYS_DIR] [--staking_epoch STAKING_EPOCH]
               [--ignore_regression_test] [--ignore_staking_test] [--debug]

Python script to test the Harmony blockchain using the hmy CLI.

optional arguments:
  -h, --help            show this help message and exit
  --test_dir TEST_DIR   Path to test directory. Default is './tests/default'
  --iterations ITERATIONS
                        Number of attempts for a successful test. Default is
                        5.
  --start_epoch START_EPOCH
                        The minimum epoch before starting tests. Default is 1.
  --rpc_endpoint_src ENDPOINT_SRC
                        Source endpoint for Cx. Default is
                        https://api.s0.b.hmny.io/
  --rpc_endpoint_dst ENDPOINT_DST
                        Destination endpoint for Cx. Default is
                        https://api.s1.b.hmny.io/
  --src_shard SRC_SHARD
                        The source shard of the Cx. Default assumes associated
                        shard from src endpoint.
  --dst_shard DST_SHARD
                        The destination shard of the Cx. Default assumes
                        associated shard from dst endpoint.
  --exp_endpoint ENDPOINT_EXP
                        Default is http://e0.b.hmny.io:5000/
  --delay TXN_DELAY     The time to wait before checking if a Cx/Tx is on the
                        blockchain. Default is 45 seconds. (Input is in
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
  --staking_epoch STAKING_EPOCH
                        The epoch to start the staking integration tests.
                        Default is 4.
  --ignore_regression_test
                        Disable the regression tests.
  --ignore_staking_test
                        Disable the staking tests.
  --debug               Enable debug printing.
```

## Notes
  - Faucet/funding accounts must have funds on shard0 and will only fund other accounts on shard0. 
  - For simplicity, all keys imported / used **MUST** have the same passphrase (set as an option). Note that this passphrase will be used to create accounts and encrypt BLS keys. 
  - **If you get that you cannot decrypt the keystore (and you are sure that the passphrase is correct), go to the CLI's keystore (path can be found with `./hmy keys location`) and delete the files that start with `_Test_key_`.**
  - Currently, this script will only import account keys that end with `.key` or `--`.
  - Regression tests that just ensure that the baseline RPC calls work are tested using `newman` (the postman JS CLI). But all other tests (like staking tests) are done in python.
  > Currently, the staking tests are **NOT** comprehensive. 

## Bugs
  - `hmy_getFilterChanges` is not being tested because of unknown params.
  - `hmy_getLogs` is not being tested because of unknown params.

## Adding tests

### Postman collection tests using newman
To run your own postman / `newman` collection (or an updated version of the regression test collection) export the collection, global variables, and environment variables to `<test_dir>/test.json`, `<test_dir>/global.json`, and `<test_dir>/env.json` respectively. For more details on how to export a test, reference [here](https://kb.datamotion.com/?ht_kb=postman-instructions-for-exporting-and-importing#how-to-export-a-collection-from-postman). For more details on how to export global variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_globals/). For more details on how to export environment variables, reference [here](https://learning.getpostman.com/docs/postman/environments_and_globals/manage_environments/)

To add a new collection to be ran by newman, just create a directory that looks like `./tests/default/` and specify it as the `--test_dir` option. **Make sure to also code up the variable setup in the python script**. Reference the `regression_test` function for an example. 

### Integration tests using hmy CLI & python
Integration tests (like the staking tests) are currently written in `test.py` and use the `pyhmy.HmyCLI` object to do most of the blockchain interaction. Moreover, `utils.py` provide common functions that are used in multiple tests.   

To add your own tests, follow the staking example already present. **IT IS IMPERATIVE** that test functions return a truthy value when they pass and a falsy value when they fail. Ideally one would create multiple small tests and chain them together into larger integration tests. 
Moreover, one should decorate their (small) test functions with `@test` so it's easy to see where something went wrong. One should also color print relevant information (either as a debug option or not) to help inform and provide context of what went wrong.    