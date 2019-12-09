#!/usr/bin/env python3
import argparse
import os
import random
import inspect
import re
import shutil
import time

import pyhmy
from utils import *

ACC_NAME_PREFIX = "_Staking_test_"
SAVED_ITEM_PATHS = []
GAS_OVERHEAD = 1  # in $one

# Constants for the test, amounts are in $one
MAX_TOTAL_DELEGATION = 30
MIN_SELF_DELEGATION = 2
AMOUNT = 3
DELEGATE = random.randint(1, 10)


def parse_args():
    parser = argparse.ArgumentParser(description='Standalone staking test using hmy CLI.')
    parser.add_argument('faucet_keystore_file', metavar='keystore-file', type=str,
                        help="Absolute path for a funded account's keystore file.")
    parser.add_argument('--keystore-passphrase', dest='faucet_keystore_passphrase', default='', type=str,
                        help="The passphrase associated with the keystore file. Default is ''.")
    parser.add_argument("--cli-binary-path", dest="cli_binary_path", default=None, type=str,
                        help="ABSOLUTE PATH of CLI binary. "
                             "Default uses the binary found in script directory if present.")
    parser.add_argument('--endpoint', dest='endpoint', type=str, default="http://localhost:9500/",
                        help="The endpoint for the test. Default is 'http://localhost:9500/'.")
    parser.add_argument("--chain-id", dest="chain_id", default="testnet", type=str,
                        help="Chain ID for the CLI. Default is 'testnet'.")
    return parser.parse_args()


def check_balance(name):
    address = CLI.get_address(name)
    return json.loads(CLI.single_call(f"hmy --node={args.endpoint} balances {address}"))


def bls_generator(count, key_dir="/tmp", filter_fn=None):
    assert os.path.isabs(key_dir)
    if filter_fn is not None:
        assert callable(filter_fn)
        assert len(inspect.signature(filter_fn).parameters) == 1, "filter function must have 1 argument"

    for i in range(count):
        while True:
            proc = CLI.expect_call(f"hmy keys generate-bls-key --bls-file-path {key_dir}/{ACC_NAME_PREFIX}bls{i}.key",
                                   timeout=3)
            proc.expect("Enter passphrase:\r\n")
            proc.sendline("")
            proc.expect("Repeat the passphrase:\r\n")
            proc.sendline("")
            bls_key = json.loads(proc.read().decode().strip())
            if filter_fn is None or filter_fn(bls_key):
                break
        yield bls_key


@announce
def import_faucet_account():
    assert os.path.isabs(args.faucet_keystore_file), "Keystore file path must be absolute"
    account_name = f"{ACC_NAME_PREFIX}faucet"
    CLI.remove_account(account_name)
    response = CLI.single_call(f"hmy keys import-ks {args.faucet_keystore_file} {account_name} "
                               f"--passphrase {args.faucet_keystore_passphrase}")
    if response.strip() != f"Imported keystore given account alias of `{account_name}`":
        raise ValueError("Could not import keystore file, check error message.")
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{account_name}")
    return account_name


@announce
def check_faucet_account(account_name):
    min_funds = MAX_TOTAL_DELEGATION + 2 * GAS_OVERHEAD
    if check_balance(account_name)[0]["amount"] < min_funds:  # For now, force funds to be in shard 0 for test.
        raise ValueError(f"Provided keystore does not have at least {min_funds} on shard 0 ({args.endpoint})")
    return True


@announce
def fund_account(from_account_name, to_account_name, amount):
    """
    Assumes from_account has funds on shard 0.
    Assumes from_account has been imported with default passphrase.
    """
    from_address = CLI.get_address(from_account_name)
    to_address = CLI.get_address(to_account_name)
    CLI.single_call(f"hmy --node={args.endpoint} transfer --from {from_address} --to {to_address} "
                    f"--from-shard 0 --to-shard 0 --amount {amount} --chain-id {args.chain_id} "
                    f"--wait-for-confirm=45", timeout=40)
    print(f"{COLOR.OKGREEN}Balances for {to_account_name} ({to_address}):{COLOR.ENDC}")
    print(f"{json.dumps(check_balance(to_account_name), indent=4)}\n")


@announce
def setup_staking_delegation_test(funding_account):
    val_acc_name = f"{ACC_NAME_PREFIX}delegation-test-validator"
    CLI.remove_account(val_acc_name)
    CLI.single_call(f"hmy keys add {val_acc_name}")
    del_acc_name = f"{ACC_NAME_PREFIX}delegation-test-delegator"
    CLI.remove_account(del_acc_name)
    CLI.single_call(f"hmy keys add {del_acc_name}")
    init_del_funds = DELEGATE + random.randint(0, int(MAX_TOTAL_DELEGATION - MIN_SELF_DELEGATION - DELEGATE - AMOUNT))
    init_val_funds = random.randint(max(AMOUNT, MIN_SELF_DELEGATION), int(MAX_TOTAL_DELEGATION - init_del_funds))
    init_del_funds += GAS_OVERHEAD
    init_val_funds += GAS_OVERHEAD
    assert init_del_funds + init_val_funds < MAX_TOTAL_DELEGATION + 2 * GAS_OVERHEAD
    fund_account(funding_account, val_acc_name, init_val_funds)
    fund_account(funding_account, del_acc_name, init_del_funds)
    return val_acc_name, del_acc_name


@test
def staking_delegation(val_name, del_name):
    assert check_balance(val_name)[0]["amount"] >= max(AMOUNT, MIN_SELF_DELEGATION)
    assert check_balance(del_name)[0]["amount"] >= DELEGATE

    val_address = CLI.get_address(val_name)
    del_address = CLI.get_address(del_name)
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{val_name}")
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{del_name}")
    print(f"{COLOR.HEADER}Validator address: {val_address}")
    print(f"Delegator address: {del_address}{COLOR.ENDC}\n")

    # Create a new validator with a fresh BLS key.
    shard_count = len(get_sharding_structure(args.endpoint)['result'])
    bls_key = list(bls_generator(1, os.getcwd(), filter_fn=lambda k: int(k["public-key"], 16) % shard_count == 0))[0]
    bls_key_path = bls_key["encrypted-private-key-path"]
    SAVED_ITEM_PATHS.append(bls_key_path)
    print(f"{COLOR.OKGREEN}New BLS key:{COLOR.ENDC}\n{json.dumps(bls_key, indent=4)}\n")
    proc = CLI.expect_call(f"hmy --node={args.endpoint} staking create-validator --validator-addr {val_address} "
                           f"--name {val_name} --identity test_account --website harmony.one "
                           f"--security-contact Daniel-VDM --details none --rate 0.1 --max-rate 0.9 "
                           f"--max-change-rate 0.05 --min-self-delegation {MIN_SELF_DELEGATION} "
                           f"--max-total-delegation {MAX_TOTAL_DELEGATION} "
                           f"--amount {AMOUNT} --bls-pubkeys {bls_key['public-key']} "
                           f"--chain-id {args.chain_id}")
    proc.expect("Enter the absolute path to the encrypted bls private key file:\r\n")
    proc.sendline(bls_key_path)
    proc.expect("Enter the bls passphrase:\r\n")
    proc.sendline("")
    proc.expect("Repeat the bls passphrase:\r\n")
    proc.sendline("")
    txn = json.loads(proc.read().decode().replace('\r', '').replace('\n', ''))
    print(f"{COLOR.OKGREEN}Created validator {val_address}:{COLOR.ENDC}\n{json.dumps(txn, indent=4)}\n")
    print(f"{COLOR.OKBLUE}Sleeping 25 seconds for finality...{COLOR.ENDC}\n")
    time.sleep(25)

    # Check the create-validator staking transaction.
    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-receipt {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Create validator transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate staking transaction

    # Check if new validator is on the blockchain.
    response = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain validator all"))
    print(f"{COLOR.OKGREEN}Current validators:{COLOR.ENDC}\n{json.dumps(response, indent=4)}\n")
    if val_address not in response["result"]:
        print(f"Newly added validator ({val_address}) is not on blockchain.")
        return False

    # Check if new validator information matches the create-validator command.
    response = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain validator information {val_address}"))
    print(f"{COLOR.OKGREEN}Added validator information:{COLOR.ENDC}\n{json.dumps(response, indent=4)}\n")
    # TODO: check if information matches the create-validator command.

    # Delegate to the new validator.
    txn = json.loads(CLI.single_call(f"hmy --node={args.endpoint} staking delegate --delegator-addr {del_address} "
                                     f"--validator-addr {val_address} --amount {DELEGATE} --chain-id {args.chain_id}"))
    print(f"{COLOR.OKGREEN}Delegated {DELEGATE} $ONE from {del_address} to {val_address}:{COLOR.ENDC}")
    print(f"{json.dumps(txn, indent=4)}\n")
    print(f"{COLOR.OKBLUE}Sleeping 25 seconds for finality...{COLOR.ENDC}\n")
    time.sleep(25)

    # Check the delegation staking transaction.
    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-receipt {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Delegate transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate transaction

    # Check if the delegation is on the blockchain.
    validator_delegation = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                                      f"delegation by-validator {val_address}"))
    delegator_delegation = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                                      f"delegation by-delegator {del_address}"))
    print(f"{COLOR.OKGREEN}Delegation (by validator):{COLOR.ENDC}\n{json.dumps(validator_delegation, indent=4)}\n")
    print(f"{COLOR.OKGREEN}Delegation (by delegator):{COLOR.ENDC}\n{json.dumps(delegator_delegation, indent=4)}\n")
    # TODO: check if information is matches

    # Delegator account collects rewards, TODO: wait until there are rewards (or timeout fail).
    txn = json.loads(CLI.single_call(f"hmy --node={args.endpoint} staking collect-rewards "
                                     f"--delegator-addr {del_address} --chain-id {args.chain_id}"))
    print(f"{COLOR.OKGREEN}Collected reward:{COLOR.ENDC}\n{json.dumps(txn, indent=4)}\n")
    print(f"{COLOR.OKBLUE}Sleeping 25 seconds for finality...{COLOR.ENDC}\n")
    time.sleep(25)

    # Check the delegator reward collection.
    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-receipt {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Rewards transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate transaction

    return True


@announce
def cleanup_and_save():
    save_dir = f"saved-test-items-{datetime.datetime.utcnow()}"
    os.mkdir(save_dir)
    for path in SAVED_ITEM_PATHS:
        shutil.move(path, save_dir)
    with open(f"{save_dir}/pw.txt", "w") as f:
        f.write("Passphrase:")
    shutil.make_archive(save_dir, "tar")
    shutil.rmtree(save_dir)


if __name__ == "__main__":
    args = parse_args()
    CLI = pyhmy.HmyCLI(environment=pyhmy.get_environment(), hmy_binary_path=args.cli_binary_path)
    version_str = re.search('version v.*-', CLI.version).group(0).split('-')[0].replace("version v", "")
    assert int(version_str) >= 164, "CLI binary is the wrong version."
    assert os.path.isfile(CLI.hmy_binary_path), "CLI binary is not found, specify it with option."
    assert is_active_shard(args.endpoint), "The shard endpoint is NOT active."

    faucet_acc_name = import_faucet_account()
    check_faucet_account(faucet_acc_name)

    v_acc_name, d_acc_name = setup_staking_delegation_test(faucet_acc_name)
    staking_delegation(v_acc_name, d_acc_name)

    cleanup_and_save()
