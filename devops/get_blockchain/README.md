# Get Blockchain for a given endpoint

A simple script to get all blocks of a blockchain.

*Note that this is currently done sequentially.*

> The script will create (or replace) the following files:
>    1) `blockchain.json`: An ordered (desc) JSON array of all the blocks
>    2) `blockchain-bad-load.json`: An ordered (desc) list of block numbers that could not be fetched.

## Usage

1) Make sure you have python3 installed and the `requests` module.
> One can install the requests module with the following command: `python3 -m pip install requests`

2) Curl the script with the following command:
```bash
curl -O https://raw.githubusercontent.com/harmony-one/harmony-ops/master/devops/get_blockchain/get_blockchain.py && chmod +x ./get_blockchain.py && ./get_blockchain.py -h
```

3) Fetch the blockchain with `./get_blockchain.py <ENDPOINT> --stats`