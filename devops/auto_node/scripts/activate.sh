#!/bin/bash
./bin/hmy staking edit-validator --validator-addr $(cat /.val_address) --active true -n $(cat /.beacon_endpoint) --passphrase-file /.wallet_passphrase