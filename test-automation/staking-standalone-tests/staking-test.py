#!/usr/bin/env python3
import argparse
import datetime
import json
import os
import random
import re
import shutil
import time

import pyhmy

ACC_NAME_PREFIX = "_Staking_test_key_"
SAVED_ITEM_PATHS = []
GAS_OVERHEAD = 10  # in $one

# Constants for the test, amounts are in $one
MAX_TOTAL_DELEGATION = 30
MIN_SELF_DELEGATION = 2
AMOUNT = 3
DELEGATE = random.randint(1, 10)


class COLOR:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


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


def cleanup_and_save():
    save_dir = f"saved-test-items-{datetime.datetime.utcnow()}"
    os.mkdir(save_dir)
    for path in SAVED_ITEM_PATHS:
        shutil.move(path, save_dir)
    with open(f"{save_dir}/pw.txt", "w") as f:
        f.write("Passphrase:")
    shutil.make_archive(save_dir, "tar")
    shutil.rmtree(save_dir)


def import_faucet_account():
    print(f"{COLOR.OKBLUE}Importing key...{COLOR.ENDC}")
    assert os.path.isabs(args.faucet_keystore_file), "Keystore file path must be absolute"
    account_name = f"{ACC_NAME_PREFIX}faucet"
    CLI.remove_account(account_name)
    response = CLI.single_call(f"hmy keys import-ks {args.faucet_keystore_file} {account_name} "
                               f"--passphrase {args.faucet_keystore_passphrase}")
    if response.strip() != f"Imported keystore given account alias of `{account_name}`":
        raise ValueError("Could not import keystore file, check error message.")
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{account_name}")
    return account_name


def check_faucet_account(account_name):
    print(f"{COLOR.OKBLUE}Validating imported key...{COLOR.ENDC}")
    account_address = CLI.get_address(account_name)
    balances = json.loads(CLI.single_call(f"hmy --node={args.endpoint} balances {account_address}"))
    min_funds = MAX_TOTAL_DELEGATION + 2 * GAS_OVERHEAD
    if balances[0]["amount"] < min_funds:  # For now, force funds to be in shard 0 for test.
        raise ValueError(f"Provided keystore does not have at least {min_funds} on shard 0")
    return True


def fund_account(from_account_name, to_account_name, amount):
    """
    Assumes from_account has funds on shard 0.
    Assumes from_account has been imported with default passphrase.
    """
    print(f"{COLOR.OKBLUE}Funding {to_account_name}{COLOR.ENDC}")
    from_address = CLI.get_address(from_account_name)
    to_address = CLI.get_address(to_account_name)
    CLI.single_call(f"hmy --node={args.endpoint} transfer --from {from_address} --to {to_address} "
                    f"--from-shard 0 --to-shard 0 --amount {amount} --chain-id {args.chain_id} "
                    f"--wait-for-confirm=45", timeout=40)
    balances = json.loads(CLI.single_call(f"hmy --node={args.endpoint} balances {to_address}"))
    print(f"{COLOR.OKGREEN}Balances for {to_account_name} ({to_address}):{COLOR.ENDC}")
    print(f"{json.dumps(balances, indent=4)}\n")


def setup_staking_delegation_test(funding_account):
    print(f"{COLOR.OKBLUE}{COLOR.BOLD}Setting up staking delegation test{COLOR.ENDC}")
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


def do_staking_delegation_test(val_name, del_name):
    print(f"\t{COLOR.OKBLUE}{COLOR.BOLD}== Start staking delegation test =={COLOR.ENDC}")

    val_address = CLI.get_address(val_name)
    del_address = CLI.get_address(del_name)
    bls_key_path = f"{os.getcwd()}/staking_delegation_test_bls.key"
    assert os.path.abspath(bls_key_path)
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{val_name}")
    SAVED_ITEM_PATHS.append(f"{CLI.keystore_path}/{del_name}")
    SAVED_ITEM_PATHS.append(bls_key_path)
    print(f"\n{COLOR.HEADER}Validator address: {val_address}")
    print(f"Delegator address: {del_address}{COLOR.ENDC}\n")

    proc = CLI.expect_call(f"hmy keys generate-bls-key --bls-file-path {bls_key_path}", timeout=3)
    proc.expect("Enter passphrase:\r\n")
    proc.sendline("")
    proc.expect("Repeat the passphrase:\r\n")
    proc.sendline("")
    bls_keys = json.loads(proc.read().decode().strip().replace('\r', '').replace('\n', ''))
    print(f"{COLOR.OKGREEN}New BLS key:{COLOR.ENDC}\n{json.dumps(bls_keys, indent=4)}\n")

    proc = CLI.expect_call(f"hmy --node={args.endpoint} staking create-validator --validator-addr {val_address} "
                           f"--name {val_name} --identity test_account --website harmony.one "
                           f"--security-contact Daniel-VDM --details none --rate 0.1 --max-rate 0.9 "
                           f"--max-change-rate 0.05 --min-self-delegation {MIN_SELF_DELEGATION} "
                           f"--max-total-delegation {MAX_TOTAL_DELEGATION} "
                           f"--amount {AMOUNT} --bls-pubkeys {bls_keys['public-key']} "
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

    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-by-hash {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Create validator transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate transaction

    response = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain validator all"))
    print(f"{COLOR.OKGREEN}Current validators:{COLOR.ENDC}\n{json.dumps(response, indent=4)}\n")
    if val_address not in response["result"]:
        RuntimeError(f"Newly added validator ({val_address}) is not on blockchain.")

    response = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain validator information {val_address}"))
    print(f"{COLOR.OKGREEN}Added validator information:{COLOR.ENDC}\n{json.dumps(response, indent=4)}\n")
    # TODO: check if information is matches

    txn = json.loads(CLI.single_call(f"hmy --node={args.endpoint} staking delegate --delegator-addr {del_address} "
                                     f"--validator-addr {val_address} --amount {DELEGATE} --chain-id {args.chain_id}"))
    print(f"{COLOR.OKGREEN}Delegated {DELEGATE} $ONE from {del_address} to {val_address}:{COLOR.ENDC}")
    print(f"{json.dumps(txn, indent=4)}\n")
    print(f"{COLOR.OKBLUE}Sleeping 25 seconds for finality...{COLOR.ENDC}\n")
    time.sleep(25)

    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-by-hash {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Delegate transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate transaction

    validator_delegation = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                                      f"delegation by-validator {val_address}"))
    delegator_delegation = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                                      f"delegation by-delegator {del_address}"))
    print(f"{COLOR.OKGREEN}Delegation (by validator):{COLOR.ENDC}\n{json.dumps(validator_delegation, indent=4)}\n")
    print(f"{COLOR.OKGREEN}Delegation (by delegator):{COLOR.ENDC}\n{json.dumps(delegator_delegation, indent=4)}\n")
    # TODO: check if information is matches

    txn = json.loads(CLI.single_call(f"hmy --node={args.endpoint} staking collect-rewards "
                                     f"--delegator-addr {del_address} --chain-id {args.chain_id}"))
    print(f"{COLOR.OKGREEN}Collected reward:{COLOR.ENDC}\n{json.dumps(txn, indent=4)}\n")
    print(f"{COLOR.OKBLUE}Sleeping 25 seconds for finality...{COLOR.ENDC}\n")
    time.sleep(25)

    transaction = json.loads(CLI.single_call(f"hmy --node={args.endpoint} blockchain "
                                             f"transaction-by-hash {txn['transaction-receipt']}"))
    print(f"{COLOR.OKGREEN}Rewards transaction:{COLOR.ENDC}\n{json.dumps(transaction, indent=4)}\n")
    # TODO: validate transaction

    print(f"\t{COLOR.HEADER}{COLOR.UNDERLINE}== Passed test! =={COLOR.ENDC}")


if __name__ == "__main__":
    args = parse_args()
    CLI = pyhmy.HmyCLI(environment=pyhmy.get_environment(), hmy_binary_path=args.cli_binary_path)
    version_str = re.search('version v.*-', CLI.version).group(0).split('-')[0].replace("version v", "")
    assert int(version_str) >= 164, "CLI binary is the wrong version."
    assert os.path.isfile(CLI.hmy_binary_path), "CLI binary is not found, specify it with option."

    faucet_account_name = import_faucet_account()
    check_faucet_account(faucet_account_name)

    val_account_name, del_account_name = setup_staking_delegation_test(faucet_account_name)
    do_staking_delegation_test(val_account_name, del_account_name)

    cleanup_and_save()
