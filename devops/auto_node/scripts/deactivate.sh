#!/bin/bash
./bin/hmy staking edit-validator --validator-addr $(cat /.val_address) --active false -n $(cat /.beacon_endpoint) --passphrase-file /.wallet_passphrase