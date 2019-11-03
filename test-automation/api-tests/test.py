#!/usr/bin/env python3
import subprocess
import os
import random
import json
import argparse
import pyhmy
import sys

ACC_NAMES_ADDED = []
args = None


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
    return parser.parse_args()


def get_balance(cli, name, node) -> dict:
    address = cli.get_address(name)
    if not address:
        return {}
    response = cli.single_call(f"hmy balances {address} --node={node}").replace("\n", "")
    return eval(response)  # Assumes that the return of CLI is list of dictionaries in plain text.


def load_keys(cli) -> None:
    print("Loading keys...")
    global ACC_NAMES_ADDED
    random_num = random.randint(-1e9, 1e9)
    key_paths = os.listdir(args.keys_dir)
    for i, key in enumerate(key_paths):
        if not os.path.isdir(f"{args.keys_dir}/{key}"):
            continue
        key_content = os.listdir(f"{args.keys_dir}/{key}")
        for f in key_content:
            if f.endswith(".key"):
                key_file_path = f"{os.getcwd()}/{args.keys_dir}/{key}/{f}"
                new_account_name = f"_test_key_{random_num}_{i}"
                CLI.remove_address(new_account_name)
                response = cli.single_call(f"keys import-ks {key_file_path} {new_account_name} "
                                           f"--passphrase={args.passphrase}").strip()
                if f"Imported keystore given account alias of `{new_account_name}`" == response:
                    ACC_NAMES_ADDED.append(new_account_name)
                break
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"


def get_raw_txn(cli, passphrase, chain_id, node, source_shard) -> str:
    """
    Must be cross shard transaction for tests.
    """
    print("Getting RawTxn...")
    assert source_shard == 0 or source_shard == 1, "Assume only 2 shards on network"
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"
    for acc_name in ACC_NAMES_ADDED:
        balances = get_balance(cli, acc_name, node)
        from_addr = cli.get_address(acc_name)
        to_addr_candidates = ACC_NAMES_ADDED.copy()
        to_addr_candidates.remove(acc_name)
        to_addr = cli.get_address(random.choice(to_addr_candidates))
        if balances[source_shard]["amount"] >= 1e-9:
            print(f"Raw transaction details:\n"
                  f"\tNode: {node}\n"
                  f"\tFrom: {from_addr}\n"
                  f"\tTo: {to_addr}\n"
                  f"\tFrom-shard: {source_shard}\n"
                  f"\tTo-shard: {1-source_shard}")
            if chain_id not in {"mainnet", "testnet", "pangaea"}:  # Must be localnet
                response = cli.single_call(f"hmy transfer --from={from_addr} --to={to_addr} "
                                           f"--from-shard={source_shard} --to-shard={1-source_shard} --amount={1e-9} "
                                           f"--dry-run")
                print("\tTransaction for localnet")
            else:
                response = cli.single_call(f"hmy --node={node} transfer --from={from_addr} --to={to_addr} "
                                           f"--from-shard={source_shard} --to-shard={1-source_shard} --amount={1e-9} "
                                           f"--chain-id={chain_id} --dry-run")
                print(f"\tTransaction for {chain_id}")
            response_lines = response.split("\n")
            assert len(response_lines) == 17, 'CLI output for transaction dry-run is not recognized, check CLI version.'
            transaction = '\n\t\t'.join(response_lines[1:15])
            print(f"\tTransaction:\n\t\t{transaction}")
            return response_lines[-2].replace("RawTxn: ", "")
    raise RuntimeError(f"None of the loaded accounts have funds on shard {source_shard}")


def setup_no_explorer(test_json, global_json, env_json):
    source_shard = 0 if ".s0." in args.hmy_endpoint_src or ":9500/" in args.hmy_endpoint_src else 1
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, source_shard=source_shard)

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint_src":
            if f":950{1-source_shard}/" in args.hmy_endpoint_src:
                global_json["values"][i]["value"] = args.hmy_endpoint_src.replace(f":950{1-source_shard}/",
                                                                                  f":950{source_shard}/")
            else:
                global_json["values"][i]["value"] = args.hmy_endpoint_src.replace(f".s{1-source_shard}.",
                                                                                  f".s{source_shard}.")
        if var["key"] == "hmy_endpoint_dst":
            if f":950{source_shard}/" in args.hmy_endpoint_dst:
                global_json["values"][i]["value"] = args.hmy_endpoint_dst.replace(f":950{source_shard}/",
                                                                                  f":950{1-source_shard}/")
            else:
                global_json["values"][i]["value"] = args.hmy_endpoint_dst.replace(f".s{source_shard}.",
                                                                                  f".s{1-source_shard}.")


def setup_only_explorer(test_json, global_json, env_json):
    if "localhost" in args.hmy_endpoint_src or "localhost" in args.hmy_exp_endpoint:
        print("\n\t[WARNING] This test is for testnet or mainnet.\n")

    source_shard = 0 if ".s0." in args.hmy_endpoint_src else 1
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, source_shard=source_shard)

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "tx_beta_endpoint":
            env_json["values"][i]["value"] = args.hmy_exp_endpoint.replace(f"e{source_shard-1}.", f"e{source_shard}.")
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay
        if var["key"] == "source_shard":
            env_json["values"][i]["value"] = source_shard

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_exp_endpoint":
            global_json["values"][i]["value"] = args.hmy_exp_endpoint
        if var["key"] == "hmy_endpoint_src":
            if f":950{1-source_shard}/" in args.hmy_endpoint_src:
                global_json["values"][i]["value"] = args.hmy_endpoint_src.replace(f":950{1-source_shard}/",
                                                                                  f":950{source_shard}/")
            else:
                global_json["values"][i]["value"] = args.hmy_endpoint_src.replace(f".s{1-source_shard}.",
                                                                                  f".s{source_shard}.")


def setup_default(test_json, global_json, env_json):
    if "localhost" in args.hmy_endpoint_src or "localhost" in args.hmy_exp_endpoint:
        print("\n\t[WARNING] This test is for testnet or mainnet.\n")

    source_shard = 0 if ".s0." in args.hmy_endpoint_src else 1
    raw_txn = get_raw_txn(CLI, passphrase=args.passphrase, chain_id=args.chain_id,
                          node=args.hmy_endpoint_src, source_shard=source_shard)

    for i, var in enumerate(env_json["values"]):
        if var["key"] == "rawTransaction":
            env_json["values"][i]["value"] = raw_txn
        if var["key"] == "tx_beta_endpoint":
            env_json["values"][i]["value"] = args.hmy_exp_endpoint.replace(f"e{source_shard-1}.", f"e{source_shard}.")
        if var["key"] == "txn_delay":
            env_json["values"][i]["value"] = args.txn_delay
        if var["key"] == "source_shard":
            env_json["values"][i]["value"] = source_shard

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint_src":
            global_json["values"][i]["value"] = args.hmy_endpoint_src.replace(f".s{1-source_shard}.",
                                                                              f".s{source_shard}.")
        if var["key"] == "hmy_endpoint_dst":
            global_json["values"][i]["value"] = args.hmy_endpoint_dst.replace(f".s{source_shard}.",
                                                                              f".s{1-source_shard}.")
        if var["key"] == "hmy_exp_endpoint":
            global_json["values"][i]["value"] = args.hmy_exp_endpoint


if __name__ == "__main__":
    args = parse_args()
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
        load_keys(CLI)

        if "Harmony API Tests - no-explorer" in test_json["info"]["name"]:
            setup_no_explorer(test_json, global_json, env_json)
        elif "Harmony API Tests - only-explorer" in test_json["info"]["name"]:
            setup_only_explorer(test_json, global_json, env_json)
        else:
            setup_default(test_json, global_json, env_json)

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
            CLI.remove_address(acc_name)
        raise err

    print("Removing imported keys from CLI's keystore...")
    for acc_name in ACC_NAMES_ADDED:
        CLI.remove_address(acc_name)
    sys.exit(proc.returncode)
