#!/bin/bash

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Validator address: $(cat /.val_address)"
echo "Validator passphrase: $(cat /.wallet_passphrase)"
echo "BLS public keys: $(cat /.bls_keys)"
echo "BLS keys passphrase: $(cat /.bls_passphrase)"
echo "Network: $(cat /.network)"
echo "Beacon Chain endpoint: $(cat /.beacon_endpoint)"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""