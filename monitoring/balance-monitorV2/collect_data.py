#bin/python3

import argparse
import os, sys, re
import json
import time
import common
import pandas as pd
import decimal as dec
import datetime as dt

def collect_data(address_list, round, output_dir = None):
    results = []
    for a in address_list:
        req = json.dumps(common.current_balance_request(a.address))
        result = common.request(common.api_base % int(a.shard), req)
        new_entry = {"address": a.address, "shard": a.shard, "index": round}
        if result == None:
            new_entry["balance"] = dec.Decimal('NAN')
        else:
            new_entry["balance"] = common.format_balance(result["result"])
        results.append(new_entry)

    if output_dir:
        output_path = os.path.join(output_dir, timestamp.strftime("%b%d%Y_%H%M"))
        write_output(pd.DataFrame(results), output_path)
    else:
        return pd.DataFrame(results)

def write_output(collected_data, output_path) -> int:
    v_print("Writing output to %s" % output_path)
    with open(output_path, 'w') as f:
        collected_data.to_csv(f, index = False)

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('-address-list', dest = 'address_list', required = True, help = 'List of ONE addresses to track')
    parser.add_argument('-output-dir', dest = 'output_dir', default = os.getcwd(), help = 'Directory for data dump')
    parser.add_argument('--verbose', action = 'store_true', help = 'Verbose for debug')

    args = parser.parse_args()

    if args.verbose:
        def v_print(s):
            print(s)
    else:
        def v_print(s):
            return

    if not os.path.exists(args.output_dir):
        os.mkdirs(output_path)

    address_list = common.read_addresses(args.address_list)

    collect_data(address_list, args.output_dir)
