#!/usr/bin/env python3
import argparse
import json
import os
import random
import subprocess
import sys
import time
import re

import pyhmy

ACC_NAMES_ADDED = []


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Wrapper python script to test API using newman.')
    parser.add_argument("--test_dir", dest="test_dir", default="./tests/default",
                        help="Path to test directory. Default is './tests/default'", type=str)
    parser.add_argument("--iterations", dest="iterations", default=5,
                        help="Number of attempts for a successful test. Default is 5.", type=int)
    parser.add_argument("--rpc_endpoint_src", dest="hmy_endpoint_src", default="https://api.s0.b.hmny.io/",
                        help="Source endpoint for Cx. Default is https://api.s0.b.hmny.io/", type=str)
    parser.add_argument("--rpc_endpoint_dst", dest="hmy_endpoint_dst", default="https://api.s1.b.hmny.io/",
                        help="Destination endpoint for Cx. Default is https://api.s1.b.hmny.io/", type=str)
    parser.add_argument("--src_shard", dest="src_shard", default=None, type=str,
                        help=f"The source shard of the Cx. Default assumes associated shard from src endpoint.")
    parser.add_argument("--dst_shard", dest="dst_shard", default=None, type=str,
                        help=f"The destination shard of the Cx. Default assumes associated shard from dst endpoint.")
    parser.add_argument("--exp_endpoint", dest="hmy_exp_endpoint", default="http://e0.b.hmny.io:5000/",
                        help="Default is http://e0.b.hmny.io:5000/", type=str)
    parser.add_argument("--delay", dest="txn_delay", default=30,
                        help="The time to wait before checking if a Cx/Tx is on the blockchain. "
                             "Default is 30 seconds. (Input is in seconds)", type=int)
    parser.add_argument("--chain_id", dest="chain_id", default="testnet",
                        help="Chain ID for the CLI. Default is 'testnet'", type=str)
    parser.add_argument("--cli_path", dest="hmy_binary_path", default=None,
                        help=f"ABSOLUTE PATH of CLI binary. "
                             f"Default uses the CLI included in pyhmy module", type=str)
    parser.add_argument("--cli_passphrase", dest="passphrase", default='',
                        help=f"Passphrase used to unlock the keystore. "
                             f"Default is ''", type=str)
    parser.add_argument("--keystore", dest="keys_dir", default="TestnetValidatorKeys",
                        help=f"Direcotry of keystore to import. Must follow the format of CLI's keystore. "
                             f"Default is ./TestnetValidatorKeys", type=str)
    parser.add_argument("--do_staking_test", dest="do_staking_test", action='store_true', default=False,
                        help="Toggle (on) the staking tests.")
    return parser.parse_args()


def get_balance(name, node) -> dict:
    address = CLI.get_address(name)
    if not address:
        return {}
    response = CLI.single_call(f"hmy balances {address} --node={node}").replace("\r", "").replace("\n", "")
    return json.loads(response)


def load_keys() -> None:
    print("Loading keys...")
    random_num = random.randint(-1e9, 1e9)
    key_paths = os.listdir(args.keys_dir)
    for i, key in enumerate(key_paths):
        if not os.path.isdir(f"{args.keys_dir}/{key}"):
            continue
        key_content = os.listdir(f"{args.keys_dir}/{key}")
        new_account_name = f"_Test_key_{random_num}_{i}"
        CLI.remove_account(new_account_name)
        for f in key_content:
            if f.startswith("."):
                continue
            if os.path.isabs(args.keys_dir):
                key_file_path = f"{args.keys_dir}/{key}/{f}"
            else:
                key_file_path = f"{os.getcwd()}/{args.keys_dir}/{key}/{f}"
            try:
                response = CLI.single_call(f"keys import-ks {key_file_path} {new_account_name} "
                                           f"--passphrase={args.passphrase}").strip()
                if f"Imported keystore given account alias of `{new_account_name}`" == response:
                    ACC_NAMES_ADDED.append(new_account_name)
                    break
            except RuntimeError as e:
                pass  # It's okay if import fails, just try next file in key's dir.
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"


def bls_generator(count):
    for _ in range(count):
        proc = CLI.expect_call("hmy keys generate-bls-key --bls-file-path /tmp/file.key")
        proc.expect("Enter passphrase\r\n")
        proc.sendline("")
        proc.expect("Repeat the passphrase:\r\n")
        proc.sendline("")
        response = proc.read().decode().strip().replace('\r', '').replace('\n', '')
        yield json.loads(response)


def cli_staking_test():  # TODO: improve staking tests
    print("Running CLI staking tests...")
    bls_keys = [d for d in bls_generator(50)]

    for acc in ACC_NAMES_ADDED:
        balance = get_balance(acc, args.hmy_endpoint_src)
        if balance[0]["amount"] < 1:
            continue
        address = CLI.get_address(acc)
        key_counts = [1, 10, 50]
        for i in key_counts:
            bls_key_string = ','.join(el["public-key"] for el in bls_keys[:i])
            staking_command = f"hmy staking create-validator --amount 1 --validator-addr {address} " \
                              f"--bls-pubkeys {bls_key_string} --identity foo --details bar --name baz " \
                              f"--max-change-rate 10 --max-rate 10 --max-total-delegation 10 " \
                              f"--min-self-delegation 1 --rate 10 --security-contact Leo  " \
                              f"--website harmony.one --node={args.hmy_endpoint_src} " \
                              f"--chain-id={args.chain_id}"
            response = CLI.single_call(staking_command)
            print(f"\nPassed creating a validator with {i} bls key(s)")
            print(f"\tCLI command: {staking_command}")
            print(f"\tStaking transaction response: {response}")
            if i == key_counts[-1]:
                return
            print(f"Sleeping {args.txn_delay} seconds for finality...\n")
            time.sleep(args.txn_delay)

    print("Failed CLI staking test.")
    sys.exit(-1)


def get_raw_txn(cli, passphrase, chain_id, node, src_shard, dst_shard) -> str:
    """
    Must be cross shard transaction for tests.

    If importing keys using 'import-ks', no passphrase is needed.
    """
    print("Getting RawTxn...")
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"
    for acc_name in ACC_NAMES_ADDED:
        balances = get_balance(acc_name, node)
        from_addr = cli.get_address(acc_name)
        to_addr_candidates = ACC_NAMES_ADDED.copy()
        to_addr_candidates.remove(acc_name)
        to_addr = cli.get_address(random.choice(to_addr_candidates))
        if balances[src_shard]["amount"] >= 1e-9:
            print(f"Raw transaction details:\n"
                  f"\tNode: {node}\n"
                  f"\tFrom: {from_addr}\n"
                  f"\tTo: {to_addr}\n"
                  f"\tFrom-shard: {src_shard}\n"
                  f"\tTo-shard: {dst_shard}")
            response = cli.single_call(f"hmy --node={node} transfer --from={from_addr} --to={to_addr} "
                                       f"--from-shard={src_shard} --to-shard={dst_shard} --amount={1e-9} "
                                       f"--chain-id={chain_id} --dry-run")
            print(f"\tTransaction for {chain_id}")
            response_lines = response.split("\n")
            assert len(response_lines) == 17, 'CLI output for transaction dry-run is not recognized, check CLI version.'
            transaction = '\n\t\t'.join(response_lines[1:15])
            print(f"\tTransaction:\n\t\t{transaction}")
            return response_lines[-2].replace("RawTxn: ", "")
    raise RuntimeError(f"None of the loaded accounts have funds on shard {src_shard}")


def get_shard_from_endpoint(endpoint):
    """
    Currently assumes <= 10 shards
    """
    re_match = re.search('\.s.\.', endpoint)
    if re_match:
        return int(re_match.group(0)[-2])
    re_match = re.search(':950./', endpoint)
    if re_match:
        return int(re_match.group(0)[-2])
    raise ValueError(f"Unknown endpoint format: {endpoint}")


def setup_newman_no_explorer(test_json, global_json, env_json):
    source_shard = args.src_shard if args.src_shard else get_shard_from_endpoint(args.hmy_endpoint_src)
    destination_shard = args.dst_shard if args.dst_shard else get_shard_from_endpoint(args.hmy_endpoint_dst)
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, src_shard=source_shard, dst_shard=destination_shard)

    if str(source_shard) not in args.hmy_endpoint_src:
        print(f"Source shard {source_shard} may not match source endpoint {args.hmy_endpoint_src}")
    if str(destination_shard) not in args.hmy_endpoint_dst:
        print(f"Destination shard {destination_shard} may not match destination endpoint {args.hmy_endpoint_dst}")

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint_src":
            global_json["values"][i]["value"] = args.hmy_endpoint_src
        if var["key"] == "hmy_endpoint_dst":
            global_json["values"][i]["value"] = args.hmy_endpoint_dst


def setup_newman_only_explorer(test_json, global_json, env_json):
    if "localhost" in args.hmy_endpoint_src or "localhost" in args.hmy_exp_endpoint:
        print("\n\t[WARNING] This test is for testnet or mainnet.\n")

    source_shard = args.src_shard if args.src_shard else get_shard_from_endpoint(args.hmy_endpoint_src)
    destination_shard = args.dst_shard if args.dst_shard else get_shard_from_endpoint(args.hmy_endpoint_dst)
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, src_shard=source_shard, dst_shard=destination_shard)

    if str(source_shard) not in args.hmy_endpoint_src:
        print(f"Source shard {source_shard} may not match source endpoint {args.hmy_endpoint_src}")
    if str(destination_shard) not in args.hmy_endpoint_dst:
        print(f"Destination shard {destination_shard} may not match destination endpoint {args.hmy_endpoint_dst}")

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "tx_beta_endpoint":
            env_json["values"][i]["value"] = args.hmy_exp_endpoint
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay
        if var["key"] == "source_shard":
            env_json["values"][i]["value"] = source_shard

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_exp_endpoint":
            global_json["values"][i]["value"] = args.hmy_exp_endpoint
        if var["key"] == "hmy_endpoint_src":
            global_json["values"][i]["value"] = args.hmy_endpoint_src


def setup_newman_default(test_json, global_json, env_json):
    if "localhost" in args.hmy_endpoint_src or "localhost" in args.hmy_exp_endpoint:
        print("\n\t[WARNING] This test is for testnet or mainnet.\n")

    source_shard = args.src_shard if args.src_shard else get_shard_from_endpoint(args.hmy_endpoint_src)
    destination_shard = args.dst_shard if args.dst_shard else get_shard_from_endpoint(args.hmy_endpoint_dst)
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, src_shard=source_shard, dst_shard=destination_shard)

    if str(source_shard) not in args.hmy_endpoint_src:
        print(f"Source shard {source_shard} may not match source endpoint {args.hmy_endpoint_src}")
    if str(destination_shard) not in args.hmy_endpoint_dst:
        print(f"Destination shard {destination_shard} may not match destination endpoint {args.hmy_endpoint_dst}")

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "tx_beta_endpoint":
            env_json["values"][i]["value"] = args.hmy_exp_endpoint
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay
        if var["key"] == "source_shard":
            env_json["values"][i]["value"] = source_shard

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint_src":
            global_json["values"][i]["value"] = args.hmy_endpoint_src
        if var["key"] == "hmy_endpoint_dst":
            global_json["values"][i]["value"] = args.hmy_endpoint_dst
        if var["key"] == "hmy_exp_endpoint":
            global_json["values"][i]["value"] = args.hmy_exp_endpoint


if __name__ == "__main__":
    args = parse_args()
    if args.chain_id not in {"mainnet", "testnet", "pangaea"}:
        args.chain_id = "testnet"
    assert os.path.isdir(args.keys_dir), "Could not find keystore directory"
    test_dir = args.test_dir

    with open(f"{test_dir}/test.json", 'r') as f:
        test_json = json.load(f)
    with open(f"{test_dir}/global.json", 'r') as f:
        global_json = json.load(f)
    with open(f"{test_dir}/env.json", 'r') as f:
        env_json = json.load(f)
    CLI = pyhmy.HmyCLI(environment=pyhmy.get_environment(), hmy_binary_path=args.hmy_binary_path)
    print(f"CLI Version: {CLI.version}")

    try:
        load_keys()

        if args.do_staking_test:
            cli_staking_test()

        # TODO: add new rpc tests
        if "Harmony API Tests - no-explorer" in test_json["info"]["name"]:
            setup_newman_no_explorer(test_json, global_json, env_json)
        elif "Harmony API Tests - only-explorer" in test_json["info"]["name"]:
            setup_newman_only_explorer(test_json, global_json, env_json)
        else:
            setup_newman_default(test_json, global_json, env_json)

        with open(f"{test_dir}/global.json", 'w') as f:
            json.dump(global_json, f)
        with open(f"{test_dir}/env.json", 'w') as f:
            json.dump(env_json, f)

        for i in range(args.iterations):
            print(f"\n\tIteration {i+1} out of {args.iterations}\n")
            proc = subprocess.Popen(["newman", "run", f"{test_dir}/test.json",
                                     "-e", f"{test_dir}/env.json",
                                     "-g", f"{test_dir}/global.json"])
            proc.wait()
            if proc.returncode == 0:
                print(f"\n\tSucceeded in {i+1} attempt(s)\n")
                break

    except (RuntimeError, KeyboardInterrupt) as err:
        print("Removing imported keys from CLI's keystore...")
        for acc_name in ACC_NAMES_ADDED:
            CLI.remove_account(acc_name)
        raise err

    print("Removing imported keys from CLI's keystore...")
    for acc_name in ACC_NAMES_ADDED:
        CLI.remove_account(acc_name)
    sys.exit(proc.returncode)
