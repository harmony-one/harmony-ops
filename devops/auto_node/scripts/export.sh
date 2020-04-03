#!/bin/bash

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Validator address: $(cat /.val_address)"
echo "Validator passphrase: $(cat /.wallet_passphrase)"
echo "BLS public key: $(cat /.bls_public_key)"
echo "BLS private key: $(cat /.bls_private_key)"
echo "Network: $(cat /.network)"
echo "Beacon Chain endpoint: $(cat /.beacon_endpoint)"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""