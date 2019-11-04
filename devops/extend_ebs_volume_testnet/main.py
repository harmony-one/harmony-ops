import os
import sys
import boto3
import botocore
from botocore.exceptions import ClientError

NETWORK = 'mainnet'

# array to store list of ip files to download from github
ip_file_array = []



def create_file_array(network):
    if network == 'mainnet':
        ip_file_array = []
    elif network == 'testnet':
        ip_file_array = []





def main():


    create_file_array(NETWORK)

    download_ipfiles_github(NETWORK)


if __name__ == "__main__":
    main()
