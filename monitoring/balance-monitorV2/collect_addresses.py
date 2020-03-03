#bin/python3

import argparse
import csv, os
import subprocess
from glob import glob

FN_PAGE = "https://harmony.one/fn-keys"
OUT_FILE = "validating_addresses.csv"

def collect_addresses(gen_file, out_file = OUT_FILE, write = True):
    with open(gen_file, 'r') as f:
        contents = [x.strip() for x in f]

    address_set = []
    for x in contents:
        if 'DeployAccount' in str(x):
            address_set = []
        else:
            if 'Index' in str(x):
                address_set.append(x)
    v_print(address_set)

    parsed_addresses = []
    for a in address_set:
        tokens = str(a).split(' ')
        v_print(tokens)
        addr = tokens[tokens.index("Address:") + 1][1:-2]
        shard = int('0x' + tokens[tokens.index("BlsPublicKey:") + 1][1:-3], 16) % 4
        parsed_addresses.append([addr, shard])
    v_print(parsed_addresses)

    if write:
        with open(out_file, 'w') as wf:
            writer = csv.writer(wf)
            writer.writerows(parsed_addresses)

    print("List of Foundational Node accounts & shard created!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--input-file', dest = 'input_file', default = FN_PAGE, help = "List of ONE addresses to track")
    parser.add_argument('--out-file', dest = 'out_file', default = OUT_FILE, help = "File to dump addresses to")
    parser.add_argument('--verbose', action = 'store_true', help = "Verbose for debug")

    args = parser.parse_args()

    if args.verbose:
        def v_print(s):
            print(s)
    else:
        def v_print(s):
            return

    collect_addresses(args.input_file, args.out_file)
