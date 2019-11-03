#!/usr/bin/env python
from utils import *
import subprocess
import pexpect
import os
import shutil
import json
import sys
import random
import requests
import time

log = get_logger(filename="testHmy.log")
ENVIRONMENT = {}
ADDRESSES = {}
KEYSTORE_PATH = ""
KEYS_ADDED = set()


def load_environment():
    global ENVIRONMENT
    try:
        # Requires the updated 'setup_bls_build_flags.sh'
        go_path = subprocess.check_output(["go", "env", "GOPATH"]).decode().strip()
        setup_script_path = f"{go_path}/src/github.com/harmony-one/harmony/scripts/setup_bls_build_flags.sh"
        env_raw = subprocess.check_output(["bash", setup_script_path, "-v"], timeout=5)
        ENVIRONMENT = json.loads(env_raw)
        ENVIRONMENT["HOME"] = os.environ.get("HOME")
    except json.decoder.JSONDecodeError as _:
        log(f"[Critical] Could not parse environment variables from setup_bls_build_flags.sh")
        sys.exit(-1)


def delete_from_keystore_by_name(name):
    log(f"[KEY DELETE] Removing {name} from keystore at {KEYSTORE_PATH}", error=False)
    key_file_path = f"{KEYSTORE_PATH}/{name}"

    try:
        shutil.rmtree(key_file_path)
    except shutil.Error as e:
        log(f"[KEY DELETE] Failed to delete dir: {key_file_path}\n"
            f"Exception: {e}")
        return

    del ADDRESSES[name]


def get_address_from_name(name):
    if name in ADDRESSES:
        return ADDRESSES[name]
    else:
        load_addresses()
        return ADDRESSES.get(name, None)


def load_addresses():
    """
    Separate function to avoid announce when loading addresses from keystore.
    """
    global ADDRESSES
    try:
        response = subprocess.check_output(["hmy", "keys", "list"], env=ENVIRONMENT).decode()
    except subprocess.CalledProcessError as err:
        raise RuntimeError(f"Could not list keys.\n"
                           f"\tGot exit code {err.returncode}. Msg: {err.output}") from err

    lines = response.split("\n")
    if "NAME" not in lines[0] or "ADDRESS" not in lines[0]:
        raise RuntimeError(f"Name or Address not found on first line if key list.")

    for line in lines[1:]:
        if not line:
            continue
        try:
            name, address = line.split("\t")
        except ValueError:
            raise RuntimeError(f"Unexpected key list format.")
        ADDRESSES[name.strip()] = address


@test_announce
def test_and_load_keystore_directory():
    """
    CRITICAL TEST
    """
    global KEYSTORE_PATH
    try:
        response = subprocess.check_output(["hmy", "keys", "location"], env=ENVIRONMENT).decode().strip()
    except subprocess.CalledProcessError as err:
        log(f"Failed: Could not get keystore path.\n"
            f"\tGot exit code {err.returncode}. Msg: {err.output}")
        return False
    if not os.path.exists(response):
        log(f"Failed: '{response}' is not a valid path")
        return False
    KEYSTORE_PATH = response
    log("Passed", error=False)
    return True


@test_announce
def test_and_load_keys_list():
    """
    CRITICAL TEST
    """
    try:
        load_addresses()
    except RuntimeError as err:
        log(f"Failed: got error: {err}")
        return False
    log("Passed", error=False)
    return True


@test_announce
def test_balance():
    """
    CRITICAL TEST

    Currently only checks that s0 endpoint balance matches.
      - Assumes that s1 balance works iff s0 balance works
    """
    with open("testHmyReferences/balance.json") as file:
        balance_ref = json.load(file)
    ref_key = balance_ref["key"]
    ref_min_bal = balance_ref["min_balance"]["shard_0"]
    url = 'http://localhost:9500/'
    payload = "{\n    \"jsonrpc\": \"2.0\",\n    \"method\": \"hmy_getBalance\",\n    \"params\": " \
              "[\n        \"" + ref_key + "\",\n        \"latest\"\n    ],\n    \"id\": 1\n}"
    headers = {
        'Content-Type': 'application/json'
    }

    try:
        cli_response = subprocess.check_output(["hmy", "balances", ref_key], env=ENVIRONMENT).decode().strip()
    except subprocess.CalledProcessError as err:
        log(f"Failed: Could not get balance.\n"
            f"Got exit code {err.returncode}. Msg: {err.output}")
        return False
    try:
        cli_response_list = eval(cli_response.strip())
    except SyntaxError:
        log(f"Failed: Unexpected format of cli_response. Got: {cli_response}")
        return False

    response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    request_bal = round(int(body["result"], 16) * 10 ** -18, 6)

    if ref_min_bal > request_bal:
        log(f"Failed: Balance for reference is {request_bal} but need at least {ref_min_bal} for test to be valid.")
        return False

    cli_s0_bal = round(cli_response_list[0]["amount"], 6)
    if cli_s0_bal != request_bal:
        log(f"Failed: cli balance shard 0 balance ({cli_s0_bal}) does not "
            f"match manual post request balance ({request_bal})")
        return False
    log("Passed", error=False)
    return True


@test_announce
def test_keys_add():
    key_name_to_add = f"random_key_{random.randint(-1e9,1e9)}"
    try:
        subprocess.check_output(["hmy", "keys", "add", key_name_to_add], env=ENVIRONMENT).decode().strip()
    except subprocess.CalledProcessError as err:
        log(f"Failed: Could not get keystore path.\n"
            f"\tGot exit code {err.returncode}. Msg: {err.output}")
        return False
    if not get_address_from_name(key_name_to_add):
        log(f"Failed: Could not get newly added key (name: {key_name_to_add})")
        return False
    KEYS_ADDED.add(key_name_to_add)
    log("Passed", error=False)
    return True


@test_announce
def test_keys_import_ks():
    pass


@test_announce
def test_keys_import_private():
    pass


@test_announce
def test_keys_mnemonics():
    with open('testHmyReferences/sdkMnemonics.json') as f:
        sdk_mnemonics = json.load(f)
        if not sdk_mnemonics:
            log("Could not load reference data.")
            return False

    passed = True
    for test in sdk_mnemonics["data"]:
        index = test["index"]
        if index != 0:  # CLI currently uses a hardcoded index of 0.
            continue

        mnemonic = test["phrase"]
        correct_address = test["addr"]
        address_name = f'testHmyAcc_{random.randint(0,1e9)}'
        while address_name in ADDRESSES:
            address_name = f'testHmyAcc_{random.randint(0,1e9)}'

        try:
            hmy = pexpect.spawn('./hmy', ['keys', 'add', address_name, '--recover', '--passphrase'], env=ENVIRONMENT)
            hmy.expect("Enter passphrase for account\r\n")
            hmy.sendline("")
            hmy.expect("Repeat the passphrase:\r\n")
            hmy.sendline("")
            hmy.expect("Enter mnemonic to recover keys from\r\n")
            hmy.sendline(mnemonic)
            hmy.wait()
            hmy.expect(pexpect.EOF)
        except pexpect.ExceptionPexpect as e:
            log(f"Exception occurred when adding a key with mnemonic."
                f"\nException: {e}")
            passed = False

        hmy_address = get_address_from_name(address_name)
        if hmy_address != correct_address or hmy_address is None:
            log(f"Address does not match sdk's address. \n"
                f"\tMnemonic: {mnemonic}\n"
                f"\tCorrect address: {correct_address}\n"
                f"\tCLI address: {hmy_address}")
            passed = False
        else:
            KEYS_ADDED.add(address_name)
    log("Passed", error=False) if passed else log("FAILED", error=False)
    return passed


@test_announce
def test_transfer():
    pass


@test_announce
def test_node():
    pass


@test_announce
def test_transfer_with_wait():
    pass


@test_announce
def test_blockchain_block_by_num():
    pass


@test_announce
def test_blockchain_known_chains():
    pass


@test_announce
def test_blockchain_version():
    pass


@test_announce
def test_txn_by_hash():
    pass


@test_announce
def test_txn_by_receipt():
    pass


if __name__ == "__main__":
    load_environment()

    tests_results = []
    try:
        log(f"Sleeping for 45 seconds to generate some funds...", error=False)
        time.sleep(45)

        tests_results = [  # Run critical tests here
            test_balance(),
            test_and_load_keystore_directory(),
            test_and_load_keys_list()
        ]

        if not all(tests_results):
            raise KeyboardInterrupt  # Stop the test early if critical tests failed

        tests_results.extend([  # Run standard tests here
            test_keys_add(),
            test_keys_mnemonics()
        ])
    except KeyboardInterrupt:
        pass  # Stop tests but still do cleanup and report

    for name in KEYS_ADDED:
        delete_from_keystore_by_name(name)

    if all(tests_results):
        print(f"\nPassed {len(tests_results)} tests!\n")
    else:
        num_failed = sum([1 for b in tests_results if not b])
        print(f"\nFailed {num_failed} tests, check logs.\n")
        sys.exit(-1)
