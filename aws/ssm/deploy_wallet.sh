#!/bin/bash

echo "downloading wallet.sh script .."
curl -O https://raw.githubusercontent.com/harmony-one/harmony/master/scripts/wallet.sh

echo "chmoding wallet.sh .."
chmod +x wallet.sh

echo "launching wallet .."
./wallet.sh -d