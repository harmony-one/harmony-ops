#!/usr/bin/env python3

# Usage: python3 validator_stats.py

import csv
import json
import argparse
import requests
import re
from collections import defaultdict

csv_link = 'https://docs.google.com/spreadsheets/d/e/2PACX-1vTUUOCAuSgP8TcA1xWY5AbxaMO7OSowYgdvaHpeMQudAZkHkJrf2sGE6TZ0hIbcy20qpZHmlC8HhCw1/pub?gid=0&single=true&output=csv'
encoding = 'utf-8'
groups = ['team', 'p-ops', 'foundational nodes', 'p-volunteer', 'hackers', 'community', 'partners']
headers = {'Content-Type': 'application/json'}

def get_all_validators(endpoint) -> list:
    v_print("-- hmy_getAllValidatorAddresses --")
    payload = {"id": "1", "jsonrpc": "2.0",
               "method": "hmy_getAllValidatorAddresses",
               "params": []}
    r = requests.request('POST', endpoint, headers = headers, data = json.dumps(payload), timeout = 30)
    return json.loads(r.content)['result']

def get_all_keys(endpoint) -> dict:
    v_print("-- hmy_getSuperCommittees --")
    payload = {"id": "1", "jsonrpc": "2.0",
               "method": "hmy_getSuperCommittees",
               "params": []}
    r = requests.request('POST', endpoint, headers = headers, data = json.dumps(payload), timeout = 30)
    return json.loads(r.content)['result']

def read_csv(csv_file) -> (dict, list):
    v_print("-- Processing CSV --")
    r = requests.get(csv_file)
    s = [x.decode(encoding) for x in r.content.splitlines()]
    d = defaultdict(list)
    v = []
    for line in csv.reader(s):
        if line[0] in groups and re.match('one1', line[6]) != None:
            v_print("Adding: %s" % line[6])
            d[line[0]].append(line[6])
            v.append(line[6])
    return d, v

def get_validator_information(endpoint, validators) -> dict:
    v_print("-- hmy_getValidatorInformation --")
    validator_information = {}
    for v in validators:
        v_print("Address: %s" % v)
        payload = {"id": "1", "jsonrpc": "2.0",
                   "method": "hmy_getValidatorInformation",
                   "params": [v]}
        r = requests.request('POST', endpoint, headers = headers, data = json.dumps(payload), timeout = 30)
        try:
            validator_information[v] = json.loads(r.content)['result']
        except:
            validator_information[v] = None
    return validator_information

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--endpoint', default = 'https://api.s0.os.hmny.io', help = 'Network endpoint')
    parser.add_argument('--csv_link', default = csv_link, help = 'File to read for groups & addresses')
    parser.add_argument('--verbose', default = False, action = 'store_true', help = 'Verbose print for debug')

    args = parser.parse_args()

    if args.verbose:
        def v_print(s):
            print(s)
    else:
        def v_print(s):
            return

    network_validators = get_all_validators(args.endpoint)
    committee = get_all_keys(args.endpoint)
    by_group, csv_validators = read_csv(args.csv_link)
    all_validators = list(set(network_validators + csv_validators))
    new_validators = [x for x in network_validators if x not in csv_validators]
    validator_information = get_validator_information(args.endpoint, network_validators)

    v_print("-- Processing data --")
    external_bls_keys = []
    for x in committee['current']['quorum-deciders'].keys():
        for y in committee['current']['quorum-deciders'][x]['committee-members']:
            if not y['is-harmony-slot']:
                external_bls_keys.append(y['bls-public-key'])

    current_validators = [v for v in network_validators if validator_information[v]['currently-in-committee'] > 0]
    earned_validators = [v for v in network_validators if validator_information[v]['lifetime']['reward-accumulated'] > 0]

    per_group_earning_validators = defaultdict(list)
    per_group_created_validators = defaultdict(list)

    for g in by_group.keys():
        for v in by_group[g]:
            if v in validator_information.keys():
                per_group_created_validators[g].append(v)
                if validator_information[v]['lifetime']['reward-accumulated'] > 0:
                    per_group_earning_validators[g].append(v)

    print("-- Total Validator Stats --")
    print("Total created validators: %d" % len(network_validators))
    print("Validators that have earned rewards: %d" % len(earned_validators))
    print("Current validators: %d" % len(current_validators))
    print("Total bls keys in committee: %d" % len(external_bls_keys))

    print()

    print("-- Per Group Validator Stats --")
    total_csv_created_validators = 0
    for g in per_group_created_validators.keys():
        c = len(per_group_created_validators[g])
        print("Group: %-20s Created validators: %d" % (g, c))
        total_csv_created_validators += c
    print("Total: %d" % total_csv_created_validators)

    print()

    total_csv_earned_validators = 0
    for g in per_group_earning_validators.keys():
        c = len(per_group_earning_validators[g])
        print("Group: %-20s Any reward earned validators: %d" % (g, c))
        total_csv_earned_validators += c
    print("Total: %d" % total_csv_earned_validators)

    print()

    print("-- New Validators --")
    for n in new_validators:
        print("Address: %s, Validator Name: %s, Security Contact: %s, Website: %s" % (n, validator_information[n]['validator']['name'], validator_information[n]['validator']['security-contact'], validator_information[n]['validator']['website']))
