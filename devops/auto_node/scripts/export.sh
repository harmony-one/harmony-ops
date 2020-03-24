#!/bin/bash

echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo "Validator wallet private key: $(cat /.val_acc_private_key)"
echo "Validator address: $(cat /.val_address)"
echo "BLS private key: $(cat /.bls_private_key)"
echo "BLS public key: $(cat /.bls_public_key)"
echo "Network: $(cat /.network)"
echo "Beacon Chain endpoint: $(cat /.beacon_endpoint)"
echo "~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~"
echo ""