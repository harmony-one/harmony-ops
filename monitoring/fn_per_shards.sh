#!/bin/bash

for i in $(seq 0 3); do echo shard$i; curl -s https://harmony.one/balances | awk ' { print $2 } ' | grep $i | wc -l; done
