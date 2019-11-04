import os
import sys
import boto3
import botocore
from botocore.exceptions import ClientError
import subprocess
from dotenv import load_dotenv
from timeit import default_timer as timer
from datetime import timedelta

# which network would you like update storage? mainnet or testnet?
NETWORK = 'mainnet'




# array to store list of ip files to download from github
ip_file_array = []

load_dotenv()
GIT_TOKEN = os.getenv('GIT_TOKEN')

def create_ip_file_array(network):
    if network == 'mainnet':
        path_mainnet_github = 'https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/'
        path_s0 = path_mainnet_github + 'shard0.txt'
        path_s1 = path_mainnet_github + 'shard1.txt'
        path_s2 = path_mainnet_github + 'shard2.txt'
        path_s3 = path_mainnet_github + 'shard3.txt'
        return [path_s0, path_s1, path_s2, path_s3]
    elif network == 'testnet':
        path_testnet_github = 'https://raw.githubusercontent.com/harmony-one/nodedb/master/testnet/'
        path_s0 = path_testnet_github + 'shard0.txt'
        path_s1 = path_testnet_github + 'shard1.txt'
        path_s2 = path_testnet_github + 'shard2.txt'
        return [path_s0, path_s1, path_s2]

def shcmd(cmd, ignore_error=False):
    # print('Doing:', cmd)
    ret = subprocess.call(cmd, shell=True)
    # print('Returned', ret, cmd)
    if ignore_error == False and ret != 0:
        raise RuntimeError("Failed to execute {}. Return code:{}".format(
            cmd, ret))
    return ret

def download_ipfiles_github(ip_array):
    for file in ip_array:
        cmd = "curl -H 'Authorization: token {token}' "\
              "-H 'Accept: application/vnd.github.v3.raw' -o /tmp/shard0.txt "\
              "{path}".format(token=GIT_TOKEN, path=file)
        shcmd(cmd)

def main():

    # create an array to store the path to download ip files
    ip_file_array = create_ip_file_array(NETWORK)
    print(ip_file_array)

    # download ip files from github
    download_ipfiles_github(ip_file_array)


if __name__ == "__main__":
    main()
