#!/usr/bin/env python3
import argparse
import os
import inspect
import random
import shutil
import time
import sys
import subprocess
import logging
from multiprocessing.pool import ThreadPool

import pexpect
from pyhmy.util import (
    json_load,
    datetime_format,
    Typgpy
)
import harmony_transaction_generator as tx_gen
from harmony_transaction_generator import account_manager
from harmony_transaction_generator import analysis

from utils import *

ACC_NAMES_ADDED = []
ACC_NAME_PREFIX = "_Test_key_"
endpoints = [
    "https://api.s0.b.hmny.io/",
    "https://api.s1.b.hmny.io/",
    "https://api.s2.b.hmny.io/",
]
tx_gen.Loggers.general.logger.addHandler(logging.StreamHandler(sys.stdout))
tx_gen.Loggers.balance.logger.addHandler(logging.StreamHandler(sys.stdout))
tx_gen.Loggers.transaction.logger.addHandler(logging.StreamHandler(sys.stdout))
tx_gen.Loggers.report.logger.addHandler(logging.StreamHandler(sys.stdout))

# TODO: fix script for latest staking CLI update...
# TODO: fix the dump of the setting JSON file...


def parse_args():
    parser = argparse.ArgumentParser(description='Python script to test the Harmony blockchain using the hmy CLI.')
    parser.add_argument("--test_dir", dest="test_dir", default="./tests/default",
                        help="Path to test directory. Default is './tests/default'", type=str)
    parser.add_argument("--endpoints", dest="endpoints", default=None,
                        help="Default is long running testnet.")
    parser.add_argument("--iterations", dest="iterations", default=5,
                        help="Number of attempts for a successful test. Default is 5.", type=int)
    parser.add_argument("--start_epoch", dest="start_epoch", default=1,
                        help="The minimum epoch of all endpoints before starting tests. Default is 1.", type=int)
    parser.add_argument("--delay", dest="txn_delay", default=45,
                        help="The time to wait before checking if a Cx/Tx is on the blockchain. "
                             "Default is 45 seconds. (Input is in seconds)", type=int)
    parser.add_argument("--chain_id", dest="chain_id", default="testnet",
                        help="Chain ID for the CLI. Default is 'testnet'", type=str)
    parser.add_argument("--cli_path", dest="hmy_binary_path", default=None,
                        help=f"ABSOLUTE PATH of CLI binary. "
                             f"Default uses the CLI included in pyhmy module", type=str)
    parser.add_argument("--passphrase", dest="passphrase", default='',
                        help=f"Passphrase used to unlock the keystore. "
                             f"Default is ''", type=str)
    parser.add_argument("--keystore", dest="keys_dir", default=None,
                        help=f"Directory of keystore to import. Must be a directory of keystore files. "
                             f"Default will look in the main repo's `.hmy` keystore.", type=str)
    parser.add_argument("--import_keys", dest="import_keys", default=None,
                        help=f"A comma separated string of private keys to be imported.", type=str)
    parser.add_argument("--staking_epoch", dest="staking_epoch", default=4,
                        help=f"The epoch to start the staking integration tests. Default is 4.", type=int)
    parser.add_argument("--ignore_regression_test", dest="ignore_regression_test", action='store_true', default=False,
                        help="Disable the regression tests.")
    parser.add_argument("--ignore_staking_test", dest="ignore_staking_test", action='store_true', default=False,
                        help="Disable the staking tests.")
    parser.add_argument("--ignore_transactions_test", dest="ignore_transactions_test", action='store_true', default=False,
                        help="Disable the transactions tests.")
    parser.add_argument("--debug", dest="debug", action='store_true', default=False,
                        help="Enable debug printing.")
    return parser.parse_args()


def setup():
    setup_pyhmy()
    pyhmy_version = cli.get_version()
    print(f"CLI Version: {pyhmy_version}")
    version_str = re.search('version v.*-', pyhmy_version).group(0).split('-')[0].replace("version v", "")
    assert int(version_str) >= 282, "CLI binary is the wrong version."
    if args.chain_id not in json_load(cli.single_call("hmy blockchain known-chains")):
        args.chain_id = "testnet"
    if args.keys_dir is None:
        args.keys_dir = f"{pyhmy.get_gopath()}/src/github.com/harmony-one/harmony/.hmy/keystore"
    args.endpoints = endpoints if args.endpoints is None else [el.strip() for el in args.endpoints.split(",")]
    for endpoint in args.endpoints:
        assert is_active_shard(endpoint), f"`{endpoint}` is not active"
    args.import_keys = [] if args.import_keys is None else [el.strip() for el in args.import_keys.split(",")]

    tx_gen.set_config({
        "AMT_PER_TXN": [1e-9, 1e-6],
        "NUM_SRC_ACC": 32,
        "NUM_SNK_ACC": 1,
        "MAX_TXN_GEN_COUNT": 100,
        "ONLY_CROSS_SHARD": False,
        "ENFORCE_NONCE": False,
        "ESTIMATED_GAS_PER_TXN": 1e-3,
        "INIT_SRC_ACC_BAL_PER_SHARD": .1,
        "TXN_WAIT_TO_CONFIRM": 60,
        "MAX_THREAD_COUNT": os.cpu_count()//2,
        "ENDPOINTS": args.endpoints,
        "CHAIN_ID": args.chain_id,
    })

    print(f"Waiting for epoch {args.start_epoch} (or later)")
    while not all(is_after_epoch(args.start_epoch - 1, ep) for ep in args.endpoints):
        time.sleep(5)
    load_keys()


def get_balance(node, name=None, address=None):
    assert name or address, "Must provide a keystore name or address"
    if not address:
        address = cli.get_address(name=name)
    assert address and address.startswith("one1")
    return json_load(cli.single_call(f"hmy --node={node} balances {address}"))


def add_key(name):
    proc = cli.expect_call(f"hmy keys add {name} --passphrase")
    process_passphrase(proc, args.passphrase)
    proc.wait()
    if args.debug:
        print(f"Added account key with name: {name}")
    ACC_NAMES_ADDED.append(name)


def get_faucet_account(min_funds):
    """
    Only looks for accounts that have funds on shard 0.
    """
    for acc_name in ACC_NAMES_ADDED:
        if float(get_balance(args.endpoints[0], name=acc_name)[0]["amount"]) >= min_funds:
            return acc_name
    raise RuntimeError(f"None of the loaded accounts have at least {min_funds} on shard 0")


def bls_generator(count, key_dir="/tmp", filter_fn=None):
    assert os.path.isabs(key_dir)
    if not os.path.exists(key_dir):
        os.makedirs(key_dir)
    if filter_fn is not None:
        assert callable(filter_fn)
        assert len(inspect.signature(filter_fn).parameters) == 1, "filter function must have 1 argument"

    for i in range(count):
        while True:
            if os.path.exists(f"{key_dir}/{ACC_NAME_PREFIX}bls{i}.key") and args.debug:
                print(
                    f"{Typgpy.WARNING}Overriding BLS key file at: {key_dir}/{ACC_NAME_PREFIX}bls{i}.key {Typgpy.ENDC}")
            bls_key = json_load(cli.single_call(f"hmy keys generate-bls-key --bls-file-path "
                                                f"{key_dir}/{ACC_NAME_PREFIX}bls{i}.key", timeout=3))
            if filter_fn is None or filter_fn(bls_key):
                break
        if args.debug:
            print(f"Generated BLS key:\n{json.dumps(bls_key, indent=4)}")
        yield bls_key


@announce
def load_keys():
    """
    Makes assumption that keyfile is not a hidden file
    """
    assert os.path.isdir(args.keys_dir), "Could not find keystore directory"
    ACC_NAMES_ADDED.extend(account_manager.load_accounts(args.keys_dir, args.passphrase, fast_load=True))
    for i, private_key in enumerate(args.import_keys):
        acc_name = f"{ACC_NAME_PREFIX}IMPORTED_PRIVATE_{i}"
        cli.remove_account(acc_name)
        cli.single_call(f"hmy keys import-private-key {private_key} {acc_name}")
        tx_gen.account_balances[acc_name] = tx_gen.get_balances(acc_name)  # Manually update the tx_gen acc bal
        ACC_NAMES_ADDED.append(acc_name)
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"
    tx_gen.write_all_logs()


@announce
def fund_account(from_account_name, to_account_name, amount):
    """
    Only funds accounts on shard 0, so assumes from account has funds on shard 0.
    """
    from_address = cli.get_address(from_account_name)
    to_address = cli.get_address(to_account_name)
    proc = cli.expect_call(f"hmy --node={args.endpoints[0]} transfer --from {from_address} --to {to_address} "
                           f"--from-shard 0 --to-shard 0 --amount {amount} --chain-id {args.chain_id} "
                           f"--timeout 60 --passphrase ", timeout=60)
    process_passphrase(proc, args.passphrase)
    response = json_load(proc.read().decode())
    if args.debug:
        print(f"Response: {json.dumps(response, indent=4)}")
        print(f"Balances for {to_account_name} ({to_address}):")
        print(f"{json.dumps(get_balance(args.endpoints[0], name=to_account_name), indent=4)}\n")
    return response


@test
def create_simple_validators(validator_count):
    """
    Returns a dictionary of added validators where key = address and value = dictionary
    of associated reference data.

    Note that each staking test assumes that the reference data will be updated (if necessary)
    as it is the single source of truth.

    TODO: Verify transaction-receipt
    """
    node = args.endpoints[0]
    amount = 3  # Must be > 1 b/c of min-self-delegation
    faucet_acc_name = get_faucet_account(validator_count * (amount + 1))  # +1/new_acc for gas overhead
    validator_data = {}

    for i, bls_key in enumerate(bls_generator(validator_count, key_dir="/tmp/simple_val")):
        val_name = f"{ACC_NAME_PREFIX}validator{i}"
        cli.remove_account(val_name)
        add_key(val_name)
        val_address = cli.get_address(val_name)
        fund_account(faucet_acc_name, val_name, amount + 1)  # +1 for gas overhead.
        rates = round(random.uniform(0, 1), 18), round(random.uniform(0, 1), 18)
        rate, max_rate = min(rates), max(rates)
        max_change_rate = round(random.uniform(0, max_rate - 1e-9), 18)
        max_total_delegation = random.randint(amount + 1, 10)  # +1 for delegation.
        proc = cli.expect_call(f"hmy --node={node} staking create-validator "
                               f"--validator-addr {val_address} --name {val_name} "
                               f"--identity test_account --website harmony.one "
                               f"--security-contact Daniel-VDM --details none --rate {rate} --max-rate {max_rate} "
                               f"--max-change-rate {max_change_rate} --min-self-delegation 1 "
                               f"--max-total-delegation {max_total_delegation} "
                               f"--amount {amount} --bls-pubkeys {bls_key['public-key']} "
                               f"--chain-id {args.chain_id} --passphrase --timeout 0 ")
        pub_key_str = bls_key["public-key"].replace("0x", "")
        proc.expect(f"For bls public key: {pub_key_str}\r\n")
        proc.expect("Enter the absolute path to the encrypted bls private key file:\r\n")
        proc.sendline(bls_key["encrypted-private-key-path"])
        proc.expect("Enter the bls passphrase:\r\n")
        proc.sendline("")  # Use default CLI passphrase
        process_passphrase(proc, args.passphrase)
        curr_epoch = get_current_epoch(node)
        proc.expect(pexpect.EOF)
        txn = json_load(proc.before.decode())
        assert "transaction-receipt" in txn.keys()
        assert txn["transaction-receipt"] is not None
        print(f"{Typgpy.OKGREEN}Sent create validator for "
              f"{val_address}:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")
        ref_data = {
            "time_created": datetime.datetime.utcnow().strftime(datetime_format),
            "last_edit_epoch": curr_epoch,
            "pub_bls_keys": [bls_key['public-key']],
            "amount": amount,
            "rate": rate,
            "max_rate": max_rate,
            "max_change_rate": max_change_rate,
            "max_total_delegation": max_total_delegation,
            "min_self_delegation": 1,
            "keystore_name": val_name,
        }
        if args.debug:
            print(f"Reference data for {val_address}: {json.dumps(ref_data, indent=4)}")
        validator_data[val_address] = ref_data
    return validator_data


@test
def check_validators(validator_data):
    """
    This test checks the validator against their respective reference data.
    """
    node = args.endpoints[0]
    all_val = json_load(cli.single_call(f"hmy --node={node} blockchain validator all"))
    assert all_val["result"] is not None
    print(f"{Typgpy.OKGREEN}Current validators:{Typgpy.ENDC}\n{json.dumps(all_val, indent=4)}\n")
    all_active_val = json_load(cli.single_call(f"hmy --node={node} blockchain validator all-active"))
    assert all_active_val["result"] is not None
    print(f"{Typgpy.OKGREEN}Current ACTIVE validators:{Typgpy.ENDC}\n{json.dumps(all_active_val, indent=4)}")

    for address, ref_data in validator_data.items():
        print(f"\n{'=' * 85}\n")
        print(f"{Typgpy.HEADER}Validator address: {address}{Typgpy.ENDC}")
        if address not in all_val["result"]:
            print(f"{Typgpy.FAIL}Validator NOT in pool of validators.")
            return False
        else:
            print(f"{Typgpy.OKGREEN}Validator in pool of validators.")
        if address not in all_active_val["result"]:
            print(f"{Typgpy.WARNING}Validator NOT in pool of ACTIVE validators.")
            # Don't throw an error, just inform.
        else:
            print(f"{Typgpy.WARNING}Validator in pool of ACTIVE validators.")
            # Don't throw an error, just inform.
        curr_epoch = get_current_epoch(node)
        val_info = json_load(cli.single_call(f"hmy --node={node} blockchain validator information {address}"))
        print(f"{Typgpy.OKGREEN}Validator information:{Typgpy.ENDC}\n{json.dumps(val_info, indent=4)}")
        if args.debug:
            print(f"Reference data for {address}: {json.dumps(ref_data, indent=4)}")
        assert val_info["result"] is not None
        reference_keys = set(map(lambda e: int(e, 16), ref_data["pub_bls_keys"]))
        for key in val_info["result"]["bls-public-keys"]:
            assert int(key, 16) in reference_keys
        assert ref_data["max_total_delegation"] * 1e18 - float(val_info["result"]["max-total-delegation"]) == 0
        assert ref_data["min_self_delegation"] * 1e18 - float(val_info["result"]["min-self-delegation"]) == 0
        commission_rates = val_info["result"]["commission"]
        assert ref_data["rate"] == float(commission_rates["rate"])
        assert ref_data["max_rate"] == float(commission_rates["max-rate"])
        assert ref_data["max_change_rate"] == float(commission_rates["max-change-rate"])
        val_delegation = json_load(cli.single_call(f"hmy blockchain delegation by-validator {address} "
                                                   f"--node={node}"))
        print(f"{Typgpy.OKGREEN}Validator delegation:{Typgpy.ENDC}\n{json.dumps(val_delegation, indent=4)}")
        assert val_delegation["result"] is not None
        contains_self_delegation = False
        for delegation in val_delegation["result"]:
            assert delegation["validator_address"] == address
            if delegation["delegator_address"] == address:
                assert not contains_self_delegation, "should not contain duplicate self delegation"
                contains_self_delegation = True
        assert contains_self_delegation
        if curr_epoch == ref_data["last_edit_epoch"]:
            print(f"\n{Typgpy.WARNING}Validator edited/created this epoch{Typgpy.ENDC}")
        print(f"\n{'=' * 85}\n")
    return True


@test
def edit_validators(validator_data):
    """
    This test edits all validators that it is given.

    TODO: fix / look into edit validator, got error: `too few elements for types.EditValidator`
    TODO: Create test to add / remove multiple BLS keys.
    TODO: Verify transaction-receipt
    """
    node = args.endpoints[0]
    for (address, ref_data), bls_key in zip(validator_data.items(),
                                            bls_generator(len(validator_data.keys()), key_dir="/tmp/edit_val")):
        max_total_delegation = ref_data['max_total_delegation'] + random.randint(1, 10)
        old_bls_key = ref_data['pub_bls_keys'].pop()
        proc = cli.expect_call(f"hmy staking edit-validator --validator-addr {address} "
                               f"--identity test_account --website harmony.one --details none "
                               f"--name {ref_data['keystore_name']} "
                               f"--max-total-delegation {max_total_delegation} "
                               f"--min-self-delegation 1 --rate {ref_data['rate']} --security-contact Leo  "
                               f"--website harmony.one --node={node} "
                               f"--remove-bls-key {old_bls_key}  --add-bls-key {bls_key['public-key']} "
                               f"--chain-id={args.chain_id} --passphrase --timeout 0 ")
        proc.expect("Enter the absolute path to the encrypted bls private key file:\r\n")
        proc.sendline(bls_key["encrypted-private-key-path"])
        proc.expect("Enter the bls passphrase:\r\n")
        proc.sendline("")  # Use default CLI passphrase
        process_passphrase(proc, args.passphrase)
        curr_epoch = get_current_epoch(node)
        proc.expect(pexpect.EOF)
        txn = json_load(proc.before.decode())
        assert "transaction-receipt" in txn.keys()
        assert txn["transaction-receipt"] is not None
        print(f"{Typgpy.OKGREEN}Sent edit validator for "
              f"{address}:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")
        ref_data["last_edit_epoch"] = curr_epoch
        ref_data["pub_bls_keys"].append(bls_key["public-key"])
        ref_data["max_total_delegation"] = max_total_delegation
    return True


@test
def create_simple_delegators(validator_data):
    """
    This test creates delegators that only delegate to 1 (unique) given validator.

    TODO: create more 'complex' delegators test.
    TODO: Verify transaction-receipt
    """
    delegator_data = {}
    node = args.endpoints[0]
    for i, (validator_address, data) in enumerate(validator_data.items()):
        account_name = f"{ACC_NAME_PREFIX}delegator{i}"
        cli.remove_account(account_name)
        add_key(account_name)
        delegator_address = cli.get_address(account_name)
        amount = random.randint(1, data["max_total_delegation"] - data["amount"])
        faucet_acc_name = get_faucet_account(amount + 2)  # 2 for 2x gas overhead.
        fund_account(faucet_acc_name, account_name, amount + 1)  # 1 for gas overhead.
        proc = cli.expect_call(f"hmy staking delegate --validator-addr {validator_address} "
                               f"--delegator-addr {delegator_address} --amount {amount} "
                               f"--node={node} --chain-id={args.chain_id} --passphrase --timeout 0")
        process_passphrase(proc, args.passphrase)
        txn = json_load(proc.read().decode())
        assert "transaction-receipt" in txn.keys()
        assert txn["transaction-receipt"] is not None
        print(f"{Typgpy.OKGREEN}Sent create delegator for "
              f"{delegator_address}:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")
        ref_data = {
            "time-created": datetime.datetime.utcnow().strftime(datetime_format),
            "validator_addresses": [validator_address],
            "amounts": [amount],
            "undelegations": [''],  # This will be a list of strings.
            "keystore_name": account_name
        }
        delegator_data[delegator_address] = ref_data
    return delegator_data


@test
def check_delegators(delegator_data):
    """
    This test checks the delegators against their respective reference data.
    """
    node = args.endpoints[0]
    for address, ref_data in delegator_data.items():
        print(f"\n{'=' * 85}")
        print(f"{Typgpy.HEADER}Delegator address: {address}{Typgpy.ENDC}")
        del_delegation = json_load(cli.single_call(f"hmy blockchain delegation by-delegator {address} "
                                                   f"--node={node}"))
        print(f"{Typgpy.OKGREEN}Delegator delegation:{Typgpy.ENDC}\n{json.dumps(del_delegation, indent=4)}")
        if args.debug:
            print(f"Reference data for {address}: {json.dumps(ref_data, indent=4)}")
        assert del_delegation["result"] is not None
        assert len(del_delegation["result"]) >= 1
        ref_del_val_addrs = set(ref_data["validator_addresses"])
        for delegation in del_delegation["result"]:
            assert address == delegation["delegator_address"]
            assert delegation["validator_address"] in ref_del_val_addrs
            index = ref_data["validator_addresses"].index(delegation["validator_address"])
            assert delegation["amount"] - ref_data["amounts"][index] * 1e18 == 0
            if len(delegation["Undelegations"]) != 0:
                assert json.dumps(delegation["Undelegations"]) == ref_data["undelegations"][index]
        print(f"{'=' * 85}\n")
    return True


@test
def undelegate(validator_data, delegator_data):
    """
    This test undelegates all from their respective validators.

    TODO: verify that this test works as intended with 'complex' delegators
    """
    undelegation_epochs = {}  # Format: (d_addr, v_addr): epoch
    node = args.endpoints[0]

    for d_address, d_ref_data in delegator_data.items():
        for v_address in d_ref_data["validator_addresses"]:
            if v_address not in validator_data.keys():
                if args.debug:
                    print(f"{Typgpy.WARNING}Reference data for validator: "
                          f"{v_address} not found, skipping.{Typgpy.ENDC}")
                continue
            index = d_ref_data["validator_addresses"].index(v_address)
            amount = d_ref_data["amounts"][index]
            undelegation_epochs[(d_address, v_address)] = get_current_epoch(node)
            proc = cli.expect_call(f"hmy staking undelegate --validator-addr {v_address} "
                                   f"--delegator-addr {d_address} --amount {amount} "
                                   f"--node={node} --chain-id={args.chain_id} --passphrase --timeout 0 ")
            process_passphrase(proc, args.passphrase)
            txn = json_load(proc.read().decode())
            assert "transaction-receipt" in txn.keys()
            assert txn["transaction-receipt"] is not None
            print(f"{Typgpy.OKGREEN}Sent undelegate {d_address} from "
                  f"{v_address}:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}\n")
    time.sleep(args.txn_delay)

    print(f"{Typgpy.OKBLUE}{Typgpy.BOLD}Verifying undelegations{Typgpy.ENDC}\n")
    for d_address, d_ref_data in delegator_data.items():
        for v_address in d_ref_data["validator_addresses"]:
            if v_address not in validator_data.keys():
                if args.debug:
                    print(f"{Typgpy.WARNING}Reference data for validator: "
                          f"{v_address} not found, skipping.{Typgpy.ENDC}")
                continue
            v_ref_data = validator_data[v_address]
            print(f"\n{'=' * 85}")
            print(f"{Typgpy.HEADER}Validator address: {v_address}{Typgpy.ENDC}")
            print(f"{Typgpy.HEADER}Delegator address: {d_address}{Typgpy.ENDC}")
            index = d_ref_data["validator_addresses"].index(v_address)
            val_info = json_load(cli.single_call(f"hmy blockchain delegation by-validator {v_address} "
                                                 f"--node={node}"))
            assert val_info["result"] is not None
            print(f"{Typgpy.OKGREEN}Validator information:{Typgpy.ENDC}\n{json.dumps(val_info, indent=4)}")
            if args.debug:
                print(f"Reference data for (validator) {v_address}: {json.dumps(v_ref_data, indent=4)}")
                print(f"Reference data for (delegator) {d_address}: {json.dumps(d_ref_data, indent=4)}")
            delegator_is_present = False
            for delegation in val_info["result"]:
                if d_address == delegation["delegator_address"]:
                    assert not delegator_is_present, "should not see same delegator twice"
                    delegator_is_present = True
                    # TODO: look into this undelegate logic and see if this is correct semantically.
                    assert len(delegation["Undelegations"]) >= 1
                    d_ref_data["undelegations"][index] = json.dumps(delegation["Undelegations"])
                    undelegation_is_present = False
                    for undelegation in delegation["Undelegations"]:
                        if 0 <= abs(undelegation["Epoch"] - undelegation_epochs[(d_address, v_address)]) <= 1:
                            if undelegation["Epoch"] != undelegation_epochs[(d_address, v_address)]:
                                print(f"{Typgpy.WARNING}WARNING: Undelegation epoch is off by one.{Typgpy.ENDC}")
                            assert not undelegation_is_present, "should not see duplicate undelegation"
                            undelegation_is_present = True
                            assert undelegation["Amount"] - d_ref_data["amounts"][index] * 1e18 == 0
                    assert undelegation_is_present
            assert delegator_is_present
            d_ref_data["amounts"][index] = 0
            print(f"{'=' * 85}\n")
    return True


@test
def collect_rewards(data):
    # TODO: put in logic to collect rewards after 7 epochs.
    node = args.endpoints[0]
    for address, _ in data.items():
        staking_command = f"hmy staking collect-rewards --delegator-addr {address} " \
                          f"--node={node} --chain-id={args.chain_id} --passphrase --timeout 0 "
        print(staking_command)
        proc = cli.expect_call(staking_command)
        process_passphrase(proc, args.passphrase)
        txn = json_load(proc.read().decode())
        assert "transaction-receipt" in txn.keys()
        assert txn["transaction-receipt"] is not None
        print(f"{Typgpy.OKGREEN}Collection rewards response:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")
    return True


@test
def create_single_validator_many_keys(bls_keys_count):
    """
    This test creates 1 validator with multiple BLS keys.
    It assumes that the CLI asks for the BLS key files in the order of the bls_key_string.

    TODO: Verify transaction-receipt
    """
    node = args.endpoints[0]
    amount = 2  # Must be > 1 b/c of min-self-delegation
    faucet_acc_name = get_faucet_account(amount + 5)  # + 5 for gas overheads.
    validator_addresses = {}

    val_name = f"{ACC_NAME_PREFIX}many_keys_validator"
    cli.remove_account(val_name)
    add_key(val_name)
    fund_account(faucet_acc_name, val_name, amount + 5)
    val_address = cli.get_address(val_name)
    rates = round(random.uniform(0, 1), 18), round(random.uniform(0, 1), 18)
    rate, max_rate = min(rates), max(rates)
    max_change_rate = round(random.uniform(0, max_rate - 1e-9), 18)
    max_total_delegation = random.randint(amount + 1, 10)
    bls_keys = [k for k in bls_generator(bls_keys_count, key_dir="/tmp/single_val_many_keys")]
    bls_key_string = ','.join(el["public-key"] for el in bls_keys)
    proc = cli.expect_call(f"hmy --node={node} staking create-validator "
                           f"--validator-addr {val_address} --name {val_name} "
                           f"--identity test_account --website harmony.one "
                           f"--security-contact Daniel-VDM --details none --rate {rate} --max-rate {max_rate} "
                           f"--max-change-rate {max_change_rate} --min-self-delegation 1 "
                           f"--max-total-delegation {max_total_delegation} "
                           f"--amount {amount} --bls-pubkeys {bls_key_string} "
                           f"--chain-id {args.chain_id} --passphrase --timeout 0 ")
    for key in bls_keys:
        pub_key_str = key["public-key"].replace("0x", "")
        proc.expect(f"For bls public key: {pub_key_str}\r\n")
        proc.expect("Enter the absolute path to the encrypted bls private key file:\r\n")
        proc.sendline(key["encrypted-private-key-path"])
        proc.expect("Enter the bls passphrase:\r\n")
        proc.sendline("")  # Use default CLI passphrase
    process_passphrase(proc, args.passphrase)
    curr_epoch = get_current_epoch(node)
    proc.expect(pexpect.EOF)
    txn = json_load(proc.before.decode())
    assert "transaction-receipt" in txn.keys()
    assert txn["transaction-receipt"] is not None
    print(f"{Typgpy.OKGREEN}Sent create validator for "
          f"{val_address}:{Typgpy.ENDC}\n{json.dumps(txn, indent=4)}\n")
    ref_data = {
        "time_created": datetime.datetime.utcnow().strftime(datetime_format),
        "last_edit_epoch": curr_epoch,
        "pub_bls_keys": [key['public-key'] for key in bls_keys],
        "amount": amount,
        "rate": rate,
        "max_rate": max_rate,
        "max_change_rate": max_change_rate,
        "max_total_delegation": max_total_delegation,
        "min_self_delegation": 1,
        "keystore_name": val_name,
    }
    if args.debug:
        print(f"Reference data for {val_address}: {json.dumps(ref_data, indent=4)}")
    validator_addresses[val_address] = ref_data
    return validator_addresses


@announce
def get_raw_cx(passphrase, chain_id, node, src_shard, dst_shard):
    """
    Must be cross shard transaction for tests.
    """
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"
    for acc_name in ACC_NAMES_ADDED:
        balances = get_balance(node, name=acc_name)
        from_addr = cli.get_address(acc_name)
        to_addr_candidates = ACC_NAMES_ADDED.copy()
        to_addr_candidates.remove(acc_name)
        to_addr = cli.get_address(random.choice(to_addr_candidates))
        if balances[src_shard]["amount"] >= 5:  # Ensure enough funds (even with high gas fees).
            print(f"Raw transaction details:\n"
                  f"\tNode: {node}")
            proc = cli.expect_call(f"hmy --node={node} transfer --from={from_addr} --to={to_addr} "
                                   f"--from-shard={src_shard} --to-shard={dst_shard} --amount={1e-9} "
                                   f"--chain-id={chain_id} --dry-run --passphrase")
            process_passphrase(proc, args.passphrase)
            response = json_load(proc.read().decode())
            print(f"\tTransaction for {chain_id}")
            print(f"{json.dumps(response, indent=4)}")
            return response['raw-transaction']
    raise RuntimeError(f"None of the loaded accounts have funds on shard {src_shard}")


@announce
def setup_newman_s0_s1(test_json, global_json, env_json):
    raw_txn = get_raw_cx(passphrase=args.passphrase, chain_id=args.chain_id,
                         node=args.endpoints[0], src_shard=0, dst_shard=1)

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint_src":
            global_json["values"][i]["value"] = args.endpoints[0]
        if var["key"] == "hmy_endpoint_dst":
            global_json["values"][i]["value"] = args.endpoints[1]


# TODO: re-work the create / edit to include wait-to-confirm so that we reduce the explicit wait time.
# TODO: rename validator and delegator address.
# TODO: Staking test where you send Cx and Tx to and from delegator and validator. Txns from other validators,
#       delegators, and regular transaction. Also make sure to do it before and after undelegation
# TODO: Undelegation test and collect rewards test.
def staking_integration_test():
    print(f"{Typgpy.UNDERLINE}{Typgpy.BOLD}== Running staking integration test =={Typgpy.ENDC}")

    local_return_values = []
    test_validators_data = create_simple_validators(validator_count=1)
    local_return_values.append(test_validators_data)

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)

    local_return_values.append(check_validators(test_validators_data))
    test_delegators_data = create_simple_delegators(test_validators_data)
    local_return_values.append(test_delegators_data)

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)

    local_return_values.append(check_delegators(test_delegators_data))

    # TODO: fix everything below this, break here....
    local_return_values.append(edit_validators(test_validators_data))

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)

    local_return_values.append(check_validators(test_validators_data))
    local_return_values.append(undelegate(test_validators_data, test_delegators_data))
    local_return_values.append(check_delegators(test_delegators_data))
    many_keys_validator_data_singleton = create_single_validator_many_keys(bls_keys_count=5)
    local_return_values.append(many_keys_validator_data_singleton)

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)

    local_return_values.append(check_validators(many_keys_validator_data_singleton))
    local_return_values.append(edit_validators(many_keys_validator_data_singleton))

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)

    local_return_values.append(check_validators(many_keys_validator_data_singleton))

    print(f"{Typgpy.OKBLUE}Sleeping {args.txn_delay} seconds for finality...{Typgpy.ENDC}")
    time.sleep(args.txn_delay)
    local_return_values.append(collect_rewards(test_validators_data))  # TODO: implement collect rewards test.
    if all(local_return_values):
        print(f"\n{Typgpy.OKGREEN}Passed{Typgpy.ENDC} {Typgpy.UNDERLINE}Staking Integration Test{Typgpy.ENDC}\n")
        return True
    print(f"\n{Typgpy.FAIL}FAILED{Typgpy.ENDC} {Typgpy.UNDERLINE}Staking Integration Test{Typgpy.ENDC}\n")
    return False


def regression_test():
    print(f"{Typgpy.UNDERLINE}{Typgpy.BOLD}== Running regression test =={Typgpy.ENDC}")

    with open(f"{args.test_dir}/test.json", 'r') as f:
        test_json = json.load(f)
    with open(f"{args.test_dir}/global.json", 'r') as f:
        global_json = json.load(f)
    with open(f"{args.test_dir}/env.json", 'r') as f:
        env_json = json.load(f)

    setup_newman_s0_s1(test_json, global_json, env_json)

    with open(f"{args.test_dir}/global.json", 'w') as f:
        json.dump(global_json, f)
    with open(f"{args.test_dir}/env.json", 'w') as f:
        json.dump(env_json, f)

    for n in range(args.iterations):
        print(f"\n\tIteration {n + 1} out of {args.iterations}\n")
        proc = subprocess.Popen(["newman", "run", f"{args.test_dir}/test.json",
                                 "-e", f"{args.test_dir}/env.json",
                                 "-g", f"{args.test_dir}/global.json"])
        proc.wait()
        if proc.returncode == 0:
            print(f"\n{Typgpy.OKGREEN}Passed{Typgpy.ENDC} {Typgpy.UNDERLINE}Regression Test{Typgpy.ENDC}"
                  f" in {n + 1} attempt(s)\n")
            return True
    print(f"\n{Typgpy.FAIL}FAILED{Typgpy.ENDC} {Typgpy.UNDERLINE}Regression Test{Typgpy.ENDC}\n")
    return False


def transactions_test():
    """
    Make sure to run this test last...
    """
    print(f"{Typgpy.UNDERLINE}{Typgpy.BOLD}== Running transactions test =={Typgpy.ENDC}")

    def log_writer(interval):
        while True:
            tx_gen.write_all_logs()
            time.sleep(interval)

    log_writer_pool = ThreadPool(processes=1)
    log_writer_pool.apply_async(log_writer, (5,))

    config = tx_gen.get_config()
    source_accounts = tx_gen.create_accounts(config["NUM_SRC_ACC"], "src_acc")
    sink_accounts = tx_gen.create_accounts(config["NUM_SNK_ACC"], "snk_acc")
    tx_gen.fund_accounts(source_accounts)
    tx_gen_pool = ThreadPool(processes=1)
    start_time = datetime.datetime.utcnow()
    tx_gen.set_batch_amount(5)
    tx_gen_pool.apply_async(lambda: tx_gen.start(source_accounts, sink_accounts))
    time.sleep(60)
    tx_gen.stop()
    end_time = datetime.datetime.utcnow()
    tx_gen.remove_accounts(source_accounts)
    tx_gen.remove_accounts(sink_accounts)
    time.sleep(90)
    report = analysis.verify_transactions(tx_gen.Loggers.transaction.filename, start_time, end_time)
    if report["received-transaction-report"]["failed-transactions-total"] == 0:
        print(f"\n{Typgpy.OKGREEN}Passed{Typgpy.ENDC} {Typgpy.UNDERLINE}Transactions Test{Typgpy.ENDC}\n")
        return True
    print(f"\n{Typgpy.FAIL}FAILED{Typgpy.ENDC} {Typgpy.UNDERLINE}Transactions Test{Typgpy.ENDC}\n")
    return False


if __name__ == "__main__":
    args = parse_args()
    setup()
    test_results = {}

    try:
        if not args.ignore_regression_test:
            test_results["Pre-staking epoch regression test"] = regression_test()

        if not args.ignore_staking_test:
            current_epoch = get_current_epoch(args.endpoints[0])
            while current_epoch < args.staking_epoch:
                print(f"Waiting for staking epoch ({args.staking_epoch}) currently epoch {current_epoch}")
                time.sleep(5)
                current_epoch = get_current_epoch(args.endpoints[0])
            test_results["Staking integration test"] = staking_integration_test()
            print(f"{Typgpy.OKGREEN}Doing regression test after staking epoch...{Typgpy.ENDC}")
            test_results["Post-staking epoch regression test"] = regression_test()

        if not args.ignore_transactions_test:
            test_results["Transactions test"] = transactions_test()

    except (RuntimeError, KeyboardInterrupt) as e:
        print("Removing imported keys from CLI's keystore...")
        for acc in ACC_NAMES_ADDED:
            cli.remove_account(acc)
        raise e from e

    print("Removing imported keys from CLI's keystore...")
    for acc in ACC_NAMES_ADDED:
        cli.remove_account(acc)
    print(f"{Typgpy.HEADER}{Typgpy.BOLD}Test Results:")
    print(json.dumps(test_results, indent=4))
    print(Typgpy.ENDC)
    sys.exit(all(test_results.values()))
