#!/usr/bin/env python
import subprocess
import os
import random
import json
import argparse
import pyhmy


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Wrapper python script to test API using newman.')
    parser.add_argument("--rpc_endpoint", dest="hmy_endpoint", default="https://api.s0.b.hmny.io/",
                        help="Default is https://api.s0.b.hmny.io/", type=str)
    parser.add_argument("--exp_endpoint", dest="hmy_exp_endpoint", default="http://e0.b.hmny.io:5000/",
                        help="Default is http://e0.b.hmny.io:5000/", type=str)
    parser.add_argument("--chain-id", dest="chain_id", default="testnet",
                        help="Chain ID for the CLI. Default is 'testnet'", type=str)
    parser.add_argument("--cli_path", dest="hmy_binary_path", default=None,
                        help=f"ABSOLUTE PATH of CLI binary. "
                             f"Default uses the CLI included in pyhmy module", type=str)
    parser.add_argument("--cli_passphrase", dest="passphrase", default="harmony-one",
                        help=f"Passphrase used to unlock the keystore. "
                             f"Default is 'harmony-one'", type=str)
    parser.add_argument("--keystore", dest="keys_dir", default="TestnetValidatorKeys",
                        help=f"Direcotry of keystore to import. Must follow the format of CLI's keystore. "
                             f"Default is ./TestnetValidatorKeys", type=str)
    return parser.parse_args()


def get_balance(cli, name, node) -> dict:
    address = cli.get_address(name)
    if not address:
        return {}
    response = cli.single_call(f"hmy balance {address} --node={node}").replace("\n", "")
    return eval(response)  # Assumes that the return of CLI is list of dictionaries in plain text.


def load_keys(cli) -> list:
    print("Loading keys...")
    acc_names_added = []
    key_paths = os.listdir(args.keys_dir)
    for i, key in enumerate(key_paths):
        if not os.path.isdir(f"{args.keys_dir}/{key}"):
            continue
        key_content = os.listdir(f"{args.keys_dir}/{key}")
        for file in key_content:
            if file.endswith(".key"):
                key_file_path = f"{os.getcwd()}/{args.keys_dir}/{key}/{file}"
                new_account_name = f"api_test_{i}"
                cli.remove_address(new_account_name)
                response = cli.single_call(f"keys import-ks {key_file_path} {new_account_name}").strip()
                if f"Imported keystore given account alias of `{new_account_name}`" != response:
                    raise RuntimeError(f"Could not import key: {key_file_path}")
                acc_names_added.append(new_account_name)
                break
    return acc_names_added


def get_raw_txn(cli, source_account_names, passphrase, chain_id, node, source_shard) -> str:
    """
    Must be cross shard transaction for tests.
    """
    print("Getting RawTxn...")
    assert source_shard == 0 or source_shard == 1, "Assume only 2 shards on network"
    assert len(source_account_names) > 1, "Must load at least 2 keys"
    for acc_name in source_account_names:
        balances = get_balance(cli, acc_name, node)
        from_addr = cli.get_address(acc_name)
        to_addr_candidates = source_account_names.copy()
        to_addr_candidates.remove(acc_name)
        to_addr = cli.get_address(random.choice(to_addr_candidates))
        if balances[source_shard]["amount"] >= 1e-9:
            if chain_id not in {"mainnet", "testnet", "pangaea"}:  # Must be localnet
                response = cli.single_call(f"hmy transfer --from={from_addr} --to={to_addr} "
                                           f"--from-shard={source_shard} --to-shard={1-source_shard} --amount={1e-9} "
                                           f"--passphrase={passphrase} --dry-run")
            else:
                response = cli.single_call(f"hmy --node={node} transfer --from={from_addr} --to={to_addr} "
                                           f"--from-shard={source_shard} --to-shard={1-source_shard} --amount={1e-9} "
                                           f"--passphrase={passphrase} --chain-id={chain_id} "
                                           f"--dry-run")
            ans = response.split("\n")[-2]
            return ans.replace("RawTxn: ", "")
    raise RuntimeError(f"None of the loaded accounts have funds on shard {source_shard}")


if __name__ == "__main__":
    args = parse_args()
    assert os.path.isdir(args.keys_dir), "Could not find keystore directory"

    with open("tests/global.json", 'r') as file:
        global_json = json.load(file)
    with open("tests/env.json", 'r') as file:
        env_json = json.load(file)
    CLI = pyhmy.HmyCLI(environment=pyhmy.get_environment(), hmy_binary_path=args.hmy_binary_path)
    print(f"CLI Version: {CLI.version}")

    acc_names_added = load_keys(CLI)
    source_shard = 0 if "s0" in args.hmy_endpoint else 1
    try:
        raw_txn = get_raw_txn(CLI, acc_names_added, passphrase=args.passphrase, chain_id=args.chain_id,
                              node=args.hmy_endpoint, source_shard=source_shard)
    except RuntimeError as err:
        for acc_name in acc_names_added:
            CLI.remove_address(acc_name)
        raise err

    for i, var in enumerate(env_json["values"]):
        if var["key"] != "rawTransaction":
            continue
        env_json["values"][i]["value"] = raw_txn

    for i, var in enumerate(global_json["values"]):
        if var["key"] == "hmy_endpoint":
            env_json["values"][i]["value"] = args.hmy_endpoint
        if var["key"] == "hmy_exp_endpoint":
            env_json["values"][i]["value"] = args.hmy_exp_endpoint

    with open("tests/global.json", 'w') as file:
        json.dump(global_json, file)
    with open("tests/env.json", 'w') as file:
        json.dump(env_json, file)

    subprocess.call(["newman", "run", "tests/test.json", "-e", "tests/env.json", "-g", "tests/global.json"])

    print("Removing imported keys from CLI's keystore...")
    for acc_name in acc_names_added:
        CLI.remove_address(acc_name)
