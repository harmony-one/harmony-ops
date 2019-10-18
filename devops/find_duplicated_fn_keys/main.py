#!/usr/bin/python

'''

Purpose:    to detect if there is a duplicated wallet address or BLS Key
Author:     Andy Wu (andy@harmony.one)
Date:       Oct 17, 2019

Usage:
$python3 main.py <file_path> <last_number_lines>

Example:
$python3 main.py /Users/bwu2/go/src/github.com/harmony-one/harmony/internal/genesis/foundational.go 320
based on the assumption we have and only have 320 FN keys to verify
'''

import sys
import re

if len(sys.argv) != 3:
    print("Usage: $python3 main.py <filepath> <nlines>")
    sys.exit(1)

fname, nlines = sys.argv[1:]
num_lines = int(nlines)

array_epoch_string = []

array_addr = []
array_bls = []

def tail(file, num_lines=num_lines):
    with open(file) as f:
        content = f.read().splitlines()

    count = len(content)
    # '-1' is used to exclude the last line which is an ending '}'
    for i in range(count-int(num_lines)-1, count-1):
        array_epoch_string.append(re.sub(r'\t', '', content[i]))


def generate_address_bls_array(array_epoch):
    for line in array_epoch:
        array_addr.append(line.split("\"")[3])
        array_bls.append(line.split("\"")[5])

def find_dup(array_test):
    seen_address = set()
    dup_address = []

    for x in array_test:
        if x not in seen_address:
            seen_address.add(x)
        else:
            dup_address.append(x)
    return dup_address

tail(fname, nlines)
generate_address_bls_array(array_epoch_string)

print("================== duplicated ADDRESS ==================")
dup_address = find_dup(array_addr)
print(dup_address)

print("================== duplicated BLS ==================")
dup_bls = find_dup(array_bls)
print(dup_bls)