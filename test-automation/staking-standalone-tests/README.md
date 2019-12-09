# Standalone automated staking testing script
## Overview
This python script automatically runs staking tests on any of Harmony's networks given a keystore file of 
an account that has sufficient funds.

## Dependencies & Setup
* Python3
* `pyhmy` module for python3 [here](https://pypi.org/project/pyhmy/). Can be installed with `python3 -m pip install pyhmy`. *A force upgrade could be needed, do so with `python3 -m pip install pyhmy --upgrade`*.
* `requests` module for python3 [here](https://pypi.org/project/requests/). Can be installed with `python3 -m pip install requests`.
* `./jq` found [here](https://stedolan.github.io/jq/).
* The [Harmony CLI binary](https://docs.harmony.one/home/command-line-interface/using-the-harmony-cli-tool) version 164 or newer (version can be check with `./hmy version`). *By default, the test script assumes that the binary is placed in this directory, but an explicit path to the binary can be set via an option.*
* The main Harmony repo cloned to `$(go env GOPATH)/src/github.com/harmony-one/harmony`.

## Sample commands
> The first argument is always the **absolute** path to the funding / faucet keystore file.

**A sample command for testnet**
```bash
python3 staking-test.py /Users/danielvdm/go/src/github.com/harmony-one/jenkins/testing-keystores/TestnetValidatorKeys/s0/one1shzkj8tty2wu230wsjc7lp9xqkwhch2ea7sjhc.key --keystore-passphrase= --endpoint=https://api.s0.b.hmny.io/ --chain-id=testnet
```

**A sample command for devnet**
```bash
python3 staking-test.py /Users/danielvdm/Desktop/hmyTest/UTC--2019-12-07T02-51-12.929866000Z-- --keystore-passphrase= --endpoint=https://api.s0.pga.hmny.io/ --chain-id=pangaea
```

**A sample command for localnet (options default to localnet)**
```bash
python3 staking-test.py /Users/danielvdm/go/src/github.com/harmony-one/jenkins/testing-keystores/LocalnetValidatorKeys/s0 --keystore-passphrase=
```

## Script assumptions
* All funding from the given account (aka funding/faucet account) will be taken and deposited on shard 0. **No logic is done to shuffle funds around to fund accounts**.

## Options
```bash
usage: staking-test.py [-h] [--keystore-passphrase FAUCET_KEYSTORE_PASSPHRASE]
                       [--cli-binary-path CLI_BINARY_PATH]
                       [--endpoint ENDPOINT] [--chain-id CHAIN_ID]
                       keystore-file

Standalone staking test using hmy CLI.

positional arguments:
  keystore-file         Absolute path for a funded account's keystore file.

optional arguments:
  -h, --help            show this help message and exit
  --keystore-passphrase FAUCET_KEYSTORE_PASSPHRASE
                        The passphrase associated with the keystore file.
                        Default is ''.
  --cli-binary-path CLI_BINARY_PATH
                        ABSOLUTE PATH of CLI binary. Default uses the binary
                        found in script directory if present.
  --endpoint ENDPOINT   The endpoint for the test. Default is
                        'http://localhost:9500/'.
  --chain-id CHAIN_ID   Chain ID for the CLI. Default is 'testnet'.
```

## Saved items
> The script stores all saved items in `saved-test-items-<UTC_TIME>.tar` in this directory at the end.

**It stores:**
* All keys generated
* All BLS key files generated
* Passphrase used for said files 
