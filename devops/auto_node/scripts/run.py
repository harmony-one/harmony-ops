import argparse
import ntpath
import os
import time
import stat
import sys
import subprocess
import random
import datetime
import json
import re
from multiprocessing.pool import ThreadPool
from threading import Lock

import pexpect
import requests
from pyhmy import (
    Typgpy,
    json_load
)
from pyhmy import cli

default_endpoint = "http://localhost:9500/"

env = os.environ
node_start_lock = Lock()


def parse_args():
    parser = argparse.ArgumentParser(description='Run a harmony sentry node')
    parser.add_argument("private_acc_key", help="Private wallet key to be used by validator of this node", type=str)
    parser.add_argument("--private_bls_key", help="Private BLS key to be used by node", type=str, default=None)
    parser.add_argument("--generate_shard", default=None,
                        help="Shard of generated bls key, only used if private key is not provided.", type=int)
    parser.add_argument("--network", help="Network to connect to (stress, staking, partner). Default: 'staking'.",
                        type=str, default='staking')
    parser.add_argument("--name", help="The `name` of the validator when creating a validator.",
                        type=str, default=f"harmony_sentry_{random.randint(0, 1e6)}")
    parser.add_argument("--duration", type=int, help="duration of how long the node is to run in seconds. "
                                                     "Default is forever.", default=float('inf'))
    parser.add_argument("--beacon_endpoint", dest="endpoint", type=str, default=default_endpoint)
    parser.add_argument("--clean", action="store_true", help="Clean directory before starting node.")
    parser.add_argument("--confirm_all", action="store_true", help="Say yes to all interaction.")
    parser.add_argument("--active", action="store_true", help="Always try to set active when EPOS status is inactive.")
    return parser.parse_args()


def setup():
    cli.environment.update(cli.download("./bin/hmy", replace=False))
    cli.set_binary("./bin/hmy")


def get_current_epoch(endpoint=default_endpoint):
    return int(get_latest_header(endpoint)["epoch"])


def get_latest_header(endpoint=default_endpoint):
    payload = """{
        "jsonrpc": "2.0",
        "method": "hmy_latestHeader",
        "params": [  ],
        "id": 1
    }"""
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    return json.loads(response.content)["result"]


def get_staking_epoch(endpoint=default_endpoint):
    payload = """{
        "jsonrpc": "2.0",
        "method": "hmy_getNodeMetadata",
        "params": [  ],
        "id": 1
    }"""
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    return int(body["result"]["chain-config"]["staking-epoch"])


def get_validator_information(address, endpoint=default_endpoint):
    payload = json.dumps({"id": "1", "jsonrpc": "2.0",
                          "method": "hmy_getValidatorInformation",
                          "params": [address]})
    headers = {
        'Content-Type': 'application/json'
    }
    response = requests.request('POST', endpoint, headers=headers, data=payload, allow_redirects=False, timeout=3)
    body = json.loads(response.content)
    return body['result']


def check_min_bal_on_s0(address, amount, endpoint=default_endpoint):
    balances = json_load(cli.single_call(f"hmy --node={endpoint} balances {address}"))
    for bal in balances:
        if bal['shard'] == 0:
            return bal['amount'] >= amount


def import_keys():
    # Import validator account
    val_acc_name = "validator"
    cli.remove_account(val_acc_name)
    cli.single_call(f"hmy keys import-private-key {args.private_acc_key} {val_acc_name}")
    val_addr = cli.get_address(val_acc_name)
    print(f"{Typgpy.OKGREEN}Imported validator account: {Typgpy.OKBLUE}{val_addr}{Typgpy.ENDC}")

    # Import / Generate BLS key
    if args.private_bls_key is not None:
        response = cli.single_call(f"hmy keys save-bls-key {args.private_bls_key}").strip()
        bls_file_path = response.split(" ")[-1]  # WARNING: assumption of output from CLI
        assert os.path.isfile(bls_file_path)
        public_bls_key = ntpath.basename(bls_file_path).split(".")[0]  # WARNING: assumption of bls-file name from CLI
        shard_id = json_load(cli.single_call(f"hmy --node={args.endpoint} utility "
                                             f"shard-for-bls {public_bls_key}"))["shard-id"]
        print(f"{Typgpy.OKGREEN}Imported BLS key for shard {shard_id}: {Typgpy.OKBLUE}{public_bls_key}{Typgpy.ENDC}")
    elif args.generate_shard is not None:
        while True:
            key = json_load(cli.single_call("hmy keys generate-bls-key"))
            public_bls_key = key['public-key']
            bls_file_path = key['encrypted-private-key-path']
            shard_id = json_load(cli.single_call(f"hmy --node={args.endpoint} utility "
                                                 f"shard-for-bls {public_bls_key}"))["shard-id"]
            if int(shard_id) != args.generate_shard:
                os.remove(bls_file_path)
            else:
                with open("/.bls_private_key", 'w') as f:
                    f.write(key['private-key'])
                print(f"{Typgpy.OKGREEN}Generated BLS key for shard {shard_id}: {Typgpy.OKBLUE}{public_bls_key}{Typgpy.ENDC}")
                break
    else:
        key = json_load(cli.single_call("hmy keys generate-bls-key"))
        with open("/.bls_private_key", 'w') as f:
            f.write(key['private-key'])
        public_bls_key = key['public-key']
        bls_file_path = key['encrypted-private-key-path']
        shard_id = json_load(cli.single_call(f"hmy --node={args.endpoint} utility "
                                             f"shard-for-bls {public_bls_key}"))["shard-id"]
        print(f"{Typgpy.OKGREEN}Generated BLS key for shard {shard_id}: {Typgpy.OKBLUE}{public_bls_key}{Typgpy.ENDC}")

    # Check BLS key with validator if it exists
    all_val = json_load(cli.single_call(f"hmy --node={args.endpoint} blockchain validator all"))["result"]
    if val_addr in all_val:
        print(f"{Typgpy.FAIL}{val_addr} already in list of validators!{Typgpy.ENDC}")
        val_info = json_load(cli.single_call(f"hmy --node={args.endpoint} "
                                             f"blockchain validator information {val_addr}"))["result"]
        bls_keys = val_info["validator"]["bls-public-keys"]
        if public_bls_key not in bls_keys:  # Add imported BLS key to existing validator if needed
            print(f"{Typgpy.FAIL}adding bls key: {public_bls_key} to validator: {val_addr}{Typgpy.ENDC}")
            proc = cli.expect_call(f"hmy --node={args.endpoint} staking edit-validator "
                                   f"--validator-addr {val_addr} --add-bls-key {public_bls_key}")
            proc.sendline("")  # WARNING: use default passphrase of CLI
            proc.expect(pexpect.EOF)
            new_val_info = json_load(cli.single_call(f"hmy --node={args.endpoint} "
                                                     f"blockchain validator information {val_addr}"))["result"]
            new_bls_keys = new_val_info["validator"]["bls-public-keys"]
            print(f"{Typgpy.FAIL}{val_addr} updated bls keys: {new_bls_keys}{Typgpy.ENDC}")

    # Save information for other scripts
    with open(os.path.abspath("/.val_address"),
              'w') as f:  # WARNING: assumption made of where to store address in other scripts.
        f.write(cli.get_address(val_acc_name))
    with open(os.path.abspath("/.bls_public_key"),
              'w') as f:  # WARNING: assumption made of where to store address in other scripts.
        f.write(public_bls_key)
    return val_acc_name, (public_bls_key, bls_file_path)


def run_node(bls_path, network, clean=False):
    try:
        node_start_lock.acquire()
        os.chdir("/root/node")
        r = requests.get("https://raw.githubusercontent.com/harmony-one/harmony/master/scripts/node.sh")
        with open("node.sh", 'w') as f:
            f.write(r.content.decode())
        st = os.stat("node.sh")
        os.chmod("node.sh", st.st_mode | stat.S_IEXEC)
        node_args = ["-I", "-N", network, "-z", "-k", bls_path]  # TODO: note this assumption in the README.
        if clean:
            node_args.append("-c")
        proc = pexpect.spawn("./node.sh", node_args, env=env, timeout=None)
        if clean:
            proc.sendline("Y")
        proc.sendline("")  # WARNING: default BLS passphrase
        time.sleep(10)  # Grace period for node to start
        node_start_lock.release()
        proc.expect(pexpect.EOF)  # Should never reach...
        raise RuntimeError("Unexpected termination of Harmony Node...")
    except KeyboardInterrupt:
        node_start_lock.release()
        proc.close()


def fund_account(address, endpoint):
    try:
        faucet_endpoint = re.sub(r"api\.s.", "faucet", endpoint)
        print(f"Addr: {faucet_endpoint}fund?address={address}")
        r = requests.get(f"{faucet_endpoint}fund?address={address}", timeout=60)
        print(f"{Typgpy.OKBLUE}Funded account: {address}\n\t{r.content.decode()}{Typgpy.ENDC}")
    except Exception as e:  # Don't terminate on any error
        print(f"{Typgpy.FAIL}Failed to fund account: {address}\n\t{e}{Typgpy.ENDC}")


def create_validator(validator_name, bls_pub_key):
    val_info = {
        "validator-addr": cli.get_address(validator_name),
        "name": args.name,
        "website": "harmony.one",
        "security-contact": "Daniel-VDM",
        "identity": "sentry",
        "amount": 10100,
        "min-self-delegation": 10000,
        "rate": 0.1,
        "max-rate": 0.75,
        "max-change-rate": 0.05,
        "max-total-delegation": 1e6,
    }
    print(f"{Typgpy.OKBLUE}Create validator information\n{Typgpy.OKGREEN}{json.dumps(val_info, indent=4)}{Typgpy.ENDC}")
    if args.confirm_all or input("Create validator? [Y]/n \n> ") in {'Y', 'y', 'yes', 'Yes'}:
        print(f"{Typgpy.OKBLUE}Checking validator...{Typgpy.ENDC}")
        staking_epoch = get_staking_epoch(args.endpoint)
        curr_epoch = get_current_epoch(args.endpoint)
        print(f"{Typgpy.OKBLUE}Verifying Epoch...{Typgpy.ENDC}")
        while curr_epoch < staking_epoch:  # WARNING: using staking epoch for extra security of configs.
            sys.stdout.write(f"\rWaiting for staking epoch ({staking_epoch}) -- current epoch: {curr_epoch}")
            sys.stdout.flush()
            time.sleep(8)  # Assumption of 8 second block time...
            curr_epoch = get_current_epoch(args.endpoint)
        print(f"{Typgpy.OKBLUE}Verifying Balance...{Typgpy.ENDC}")
        if not check_min_bal_on_s0(val_info['validator-addr'], val_info['amount'], args.endpoint):
            fund_account(cli.get_address(validator_name), args.endpoint)
        print(f"{Typgpy.OKBLUE}Verifying Node Sync...{Typgpy.ENDC}")
        node_start_lock.acquire()
        curr_epoch = get_latest_header("http://localhost:9500/")['epoch']
        ref_epoch = get_latest_header(args.endpoint)['epoch']
        while curr_epoch != ref_epoch:
            sys.stdout.write(
                f"\rWaiting for node to sync with chain epoch ({ref_epoch}) -- current epoch: {curr_epoch}")
            sys.stdout.flush()
            time.sleep(2)
            curr_epoch = get_latest_header("http://localhost:9500/")['epoch']
            ref_epoch = get_latest_header(args.endpoint)['epoch']
        print(f"\n{Typgpy.OKBLUE}Sending create validator transaction...{Typgpy.ENDC}")
        os.chdir("/root")
        proc = cli.expect_call(f"hmy --node={args.endpoint} staking create-validator "
                               f"--validator-addr {val_info['validator-addr']} --name {val_info['name']} "
                               f"--identity {val_info['identity']} --website {val_info['website']} "
                               f"--security-contact {val_info['security-contact']} --details none "
                               f"--rate {val_info['rate']} --max-rate {val_info['max-rate']} "
                               f"--max-change-rate {val_info['max-change-rate']} "
                               f"--min-self-delegation {val_info['min-self-delegation']} "
                               f"--max-total-delegation {val_info['max-total-delegation']} "
                               f"--amount {val_info['amount']} --bls-pubkeys {bls_pub_key} ")
        proc.expect("Enter the bls passphrase:\r\n")
        proc.sendline("")  # Use default CLI passphrase
        proc.expect(pexpect.EOF)
        try:
            response = json_load(proc.before.decode())
            print(f"{Typgpy.OKBLUE}Created Validator!\n{Typgpy.OKGREEN}{json.dumps(response, indent=4)}{Typgpy.ENDC}")
        except Exception:  # WARNING: catching all errors
            print(f"{Typgpy.FAIL}Failed to create validator! Msg:\n{proc.before.decode()}{Typgpy.ENDC}")
        node_start_lock.release()


def check_and_activate(address, epos_status):
    if "not eligible" in epos_status or "not signing" in epos_status:
        print(f"{Typgpy.FAIL}Node not active, reactivating...{Typgpy.ENDC}")
        cli.single_call(f"hmy staking edit-validator --validator-addr {address} --active true --node {args.endpoint}")


if __name__ == "__main__":
    args = parse_args()
    setup()
    val_name, (bls_key, bls_key_path) = import_keys()
    val_addr = cli.get_address(val_name)
    print(f"{Typgpy.HEADER}Starting node!{Typgpy.ENDC}")
    try:
        start_time = time.time()
        ThreadPool(processes=1).apply_async(lambda: run_node(bls_key_path, args.network, clean=args.clean))
        create_validator(val_name, bls_key)
        node_start_lock.acquire()
        curr_time = time.time()
        while curr_time - start_time < args.duration:
            try:
                epos_status = get_validator_information(val_addr, args.endpoint)['epos-status']
                print(f"{Typgpy.HEADER}EPOS status:  {Typgpy.OKGREEN}{epos_status}{Typgpy.ENDC}")
                if args.active:
                    check_and_activate(val_addr, epos_status)
            except Exception as e:
                print(f"{Typgpy.FAIL}Error when checking and activating validator. Error: {e}{Typgpy.ENDC}")
            print(f"{Typgpy.HEADER}This node's latest header at {datetime.datetime.utcnow()}\n"
                  f"{Typgpy.OKGREEN}{json.dumps(get_latest_header('http://localhost:9500/'), indent=4)}{Typgpy.ENDC}")
            time.sleep(15)
    except KeyboardInterrupt as e:
        print(f"{Typgpy.OKGREEN}Killing all harmony processes...{Typgpy.ENDC}")
        subprocess.check_call(["killall", "harmony"])
        raise e
