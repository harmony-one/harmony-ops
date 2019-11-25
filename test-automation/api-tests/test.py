#!/usr/bin/env python3
import argparse
import json
import os
import random
import re
import subprocess
import shutil
import sys
import time

import pyhmy
import requests

ACC_NAMES_ADDED = []
ACC_NAME_PREFIX = "_Test_key_"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Wrapper python script to test API using newman.')
    parser.add_argument("--test_dir", dest="test_dir", default="./tests/default",
                        help="Path to test directory. Default is './tests/default'", type=str)
    parser.add_argument("--iterations", dest="iterations", default=5,
                        help="Number of attempts for a successful test. Default is 5.", type=int)
    parser.add_argument("--start_epoch", dest="start_epoch", default=1,
                        help="The minimum epoch before starting tests. Default is 1.", type=int)
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
    parser.add_argument("--ignore_regression_test", dest="ignore_regression_test", action='store_true', default=False,
                        help="Disable the regression tests.")
    parser.add_argument("--ignore_staking_test", dest="ignore_staking_test", action='store_true', default=False,
                        help="Disable the staking tests.")
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
        account_name = f"{ACC_NAME_PREFIX}{random_num}_{i}"
        CLI.remove_account(account_name)
        for file_name in key_content:
            if not file_name.endswith(".key"):  # Strong assumption about key file, some valid files may be ignored.
                continue
            from_key_file_path = f"{os.path.abspath(args.keys_dir)}/{key}/{file_name}"
            to_key_file_path = f"{CLI.keystore_path}/{account_name}"
            if not os.path.isdir(to_key_file_path):
                os.mkdir(to_key_file_path)
            shutil.copy(from_key_file_path, to_key_file_path)
            try:
                address = CLI.get_address(account_name)
                names_with_address = CLI.get_accounts(address)
                if len(names_with_address) > 1:  # Remove duplicate accounts as passphrase may fail.
                    for name in names_with_address:
                        if not name.startswith(ACC_NAME_PREFIX):
                            print(f"[!] Removing {name} ({address}) from keystore as it conflicts with imported key")
                            CLI.remove_account(name)
            except AttributeError:
                print("[!] pyhmy is out of date. Upgrade with:\n\t python3 -m pip install pyhmy --upgrade\n")
            ACC_NAMES_ADDED.append(account_name)
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"


def is_after_epoch(n):
    url = 'http://localhost:9500/'
    payload = """{
        "jsonrpc": "2.0",
        "method": "hmy_latestHeader",
        "params": [  ],
        "id": 1
    }"""
    headers = {
        'Content-Type': 'application/json'
    }
    try:
        response = requests.request('POST', url, headers=headers, data=payload, allow_redirects=False, timeout=3)
        body = json.loads(response.content)
        return int(body["result"]["epoch"]) > n
    except (requests.ConnectionError, KeyError):
        return False


def create_validator():
    print("== Creating validators ==")

    bls_keys_for_new_val = [
        "1480fca328daaddd3487195c5500969ecccbb806b6bf464734e0e3ad18c64badfae8578d76e2e9281b6a3645d056960a",
        "9d657b1854d6477dba8bca9606f6ac884df308558f2b3b545fc76a9ef02abc87d3518cf1134d21acf03036cea2820f02",
        "e2c13c84c8f2396cf7180d5026e048e59ec770a2851003f1f2ab764a79c07463681ed7ddfe62bc4d440526a270891c86",
        "249976f984f30306f800ef42fb45272b391cfdd17f966e093a9f711e30f66f77ecda6c367bf79afc9fa31a1789e9ee8e"
    ]

    # Sourced from harmony/test/config/local-resharding.txt (Keys must be in provided keystore).
    foundational_node_data = [
        ("one1ghkz3frhske7emk79p7v2afmj4a5t0kmjyt4s5",
         "eca09c1808b729ca56f1b5a6a287c6e1c3ae09e29ccf7efa35453471fcab07d9f73cee249e2b91f5ee44eb9618be3904"),
        ("one1d7jfnr6yraxnrycgaemyktkmhmajhp8kl0yahv",
         "f47238daef97d60deedbde5302d05dea5de67608f11f406576e363661f7dcbc4a1385948549b31a6c70f6fde8a391486"),
        ("one1r4zyyjqrulf935a479sgqlpa78kz7zlcg2jfen",
         "fc4b9c535ee91f015efff3f32fbb9d32cdd9bfc8a837bb3eee89b8fff653c7af2050a4e147ebe5c7233dc2d5df06ee0a"),
        ("one1p7ht2d4kl8ve7a8jxw746yfnx4wnfxtp8jqxwe",
         "ca86e551ee42adaaa6477322d7db869d3e203c00d7b86c82ebee629ad79cb6d57b8f3db28336778ec2180e56a8e07296"),
        ("one1z05g55zamqzfw9qs432n33gycdmyvs38xjemyl",
         "95117937cd8c09acd2dfae847d74041a67834ea88662a7cbed1e170350bc329e53db151e5a0ef3e712e35287ae954818"),
        ("one1ljznytjyn269azvszjlcqvpcj6hjm822yrcp2e",
         "68ae289d73332872ec8d04ac256ca0f5453c88ad392730c5741b6055bc3ec3d086ab03637713a29f459177aaa8340615"),
        ("one1uyshu2jgv8w465yc8kkny36thlt2wvel89tcmg",
         "a547a9bf6fdde4f4934cde21473748861a3cc0fe8bbb5e57225a29f483b05b72531f002f8187675743d819c955a86100"),
        ("one103q7qe5t2505lypvltkqtddaef5tzfxwsse4z7",
         "678ec9670899bf6af85b877058bea4fc1301a5a3a376987e826e3ca150b80e3eaadffedad0fedfa111576fa76ded980c"),
        ("one1658znfwf40epvy7e46cqrmzyy54h4n0qa73nep",
         "576d3c48294e00d6be4a22b07b66a870ddee03052fe48a5abbd180222e5d5a1f8946a78d55b025de21635fd743bbad90"),
        ("one1d2rngmem4x2c6zxsjjz29dlah0jzkr0k2n88wc",
         "16513c487a6bb76f37219f3c2927a4f281f9dd3fd6ed2e3a64e500de6545cf391dd973cc228d24f9bd01efe94912e714")
    ]

    added_validators = []

    while not is_after_epoch(0):
        print("Waiting for epoch 1...")
        time.sleep(5)

    for key in bls_keys_for_new_val:
        account_name = f"{ACC_NAME_PREFIX}{random.randint(-1e6, 1e6)}"
        proc = CLI.expect_call(f"hmy keys add {account_name} --passphrase")
        proc.expect("Enter passphrase\r\n")
        proc.sendline(f"{args.passphrase}")
        proc.expect("Repeat the passphrase:\r\n")
        proc.sendline(f"{args.passphrase}")
        proc.wait()
        address = CLI.get_address(account_name)
        added_validators.append(address)
        staking_command = f"hmy staking create-validator --amount 1 " \
                          f"--validator-addr {address} " \
                          f"--bls-pubkeys {key} --identity foo --details bar --name baz " \
                          f"--max-change-rate 0.1 --max-rate 0.2 --max-total-delegation 10 " \
                          f"--min-self-delegation 1 --rate 0.1 --security-contact Leo  " \
                          f"--website harmony.one --passphrase={args.passphrase}"
        ACC_NAMES_ADDED.append(account_name)
        print(f"Staking command response for {address}: ", CLI.single_call(staking_command))

    for address, key in foundational_node_data:
        added_validators.append(address)
        staking_command = f"hmy staking create-validator --amount 1 " \
                          f"--validator-addr {address} " \
                          f"--bls-pubkeys {key} --identity foo --details bar --name baz " \
                          f"--max-change-rate 0.1 --max-rate 0.2 --max-total-delegation 10 " \
                          f"--min-self-delegation 1 --rate 0.1 --security-contact Leo  " \
                          f"--website harmony.one --passphrase={args.passphrase}"
        print(f"Staking command response for {address}: ", CLI.single_call(staking_command))

    print("Validators added: ", added_validators)


def bls_generator(count):
    for _ in range(count):
        proc = CLI.expect_call("hmy keys generate-bls-key --bls-file-path /tmp/file.key")
        proc.expect("Enter passphrase\r\n")
        proc.sendline("")
        proc.expect("Repeat the passphrase:\r\n")
        proc.sendline("")
        response = proc.read().decode().strip().replace('\r', '').replace('\n', '')
        yield json.loads(response)


def create_validator_many_keys():
    print("== Running CLI staking tests ==")
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
                              f"--max-change-rate 0.1 --max-rate 0.2 --max-total-delegation 10 " \
                              f"--min-self-delegation 1 --rate 0.1 --security-contact Leo  " \
                              f"--website harmony.one --node={args.hmy_endpoint_src} " \
                              f"--chain-id={args.chain_id} --passphrase={args.passphrase}"
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


def get_raw_txn(passphrase, chain_id, node, src_shard, dst_shard) -> str:
    """
    Must be cross shard transaction for tests.

    If importing keys using 'import-ks', no passphrase is needed.
    """
    print("== Getting raw transaction ==")
    assert len(ACC_NAMES_ADDED) > 1, "Must load at least 2 keys and must match CLI's keystore format"
    for acc_name in ACC_NAMES_ADDED:
        balances = get_balance(acc_name, node)
        from_addr = CLI.get_address(acc_name)
        to_addr_candidates = ACC_NAMES_ADDED.copy()
        to_addr_candidates.remove(acc_name)
        to_addr = CLI.get_address(random.choice(to_addr_candidates))
        if balances[src_shard]["amount"] >= 5:  # Ensure enough funds (even with high gas fees).
            print(f"Raw transaction details:\n"
                  f"\tNode: {node}\n"
                  f"\tFrom: {from_addr}\n"
                  f"\tTo: {to_addr}\n"
                  f"\tFrom-shard: {src_shard}\n"
                  f"\tTo-shard: {dst_shard}")
            response = CLI.single_call(f"hmy --node={node} transfer --from={from_addr} --to={to_addr} "
                                       f"--from-shard={src_shard} --to-shard={dst_shard} --amount={1e-9} "
                                       f"--chain-id={chain_id} --dry-run --passphrase={passphrase}")
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
    raw_txn = get_raw_txn(passphrase=args.passphrase, chain_id=args.chain_id,
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
    raw_txn = get_raw_txn(passphrase=args.passphrase, chain_id=args.chain_id,
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
    raw_txn = get_raw_txn(passphrase=args.passphrase, chain_id=args.chain_id,
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
    print("\n\t== Starting Tests ==\n")
    if args.chain_id not in {"mainnet", "testnet", "pangaea"}:
        args.chain_id = "testnet"
    assert os.path.isdir(args.keys_dir), "Could not find keystore directory"

    CLI = pyhmy.HmyCLI(environment=pyhmy.get_environment(), hmy_binary_path=args.hmy_binary_path)
    exit_code = 0
    print(f"CLI Version: {CLI.version}")

    try:
        load_keys()

        print(f"Waiting for epoch {args.start_epoch} (or later)")
        while not is_after_epoch(args.start_epoch-1):
            time.sleep(5)

        if not args.ignore_staking_test:
            create_validator()
            create_validator_many_keys()

        if not args.ignore_regression_test:
            with open(f"{args.test_dir}/test.json", 'r') as f:
                test_json = json.load(f)
            with open(f"{args.test_dir}/global.json", 'r') as f:
                global_json = json.load(f)
            with open(f"{args.test_dir}/env.json", 'r') as f:
                env_json = json.load(f)

            if "Harmony API Tests - no-explorer" in test_json["info"]["name"]:
                setup_newman_no_explorer(test_json, global_json, env_json)
            elif "Harmony API Tests - only-explorer" in test_json["info"]["name"]:
                setup_newman_only_explorer(test_json, global_json, env_json)
            else:
                setup_newman_default(test_json, global_json, env_json)

            with open(f"{args.test_dir}/global.json", 'w') as f:
                json.dump(global_json, f)
            with open(f"{args.test_dir}/env.json", 'w') as f:
                json.dump(env_json, f)

            for i in range(args.iterations):
                print(f"\n\tIteration {i+1} out of {args.iterations}\n")
                proc = subprocess.Popen(["newman", "run", f"{args.test_dir}/test.json",
                                         "-e", f"{args.test_dir}/env.json",
                                         "-g", f"{args.test_dir}/global.json"])
                proc.wait()
                if proc.returncode == 0:
                    print(f"\n\tSucceeded in {i+1} attempt(s)\n")
                    break
                exit_code = proc.returncode

    except (RuntimeError, KeyboardInterrupt) as err:
        print("Removing imported keys from CLI's keystore...")
        for acc_name in ACC_NAMES_ADDED:
            CLI.remove_account(acc_name)
        raise err

    print("Removing imported keys from CLI's keystore...")
    for acc_name in ACC_NAMES_ADDED:
        CLI.remove_account(acc_name)
    sys.exit(exit_code)
