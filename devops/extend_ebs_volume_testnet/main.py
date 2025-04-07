import os
import pprint
import sys
import boto3
import time
import botocore
from botocore.exceptions import ClientError
import subprocess
from dotenv import load_dotenv
from timeit import default_timer as timer
from datetime import timedelta

# which network would you like update storage? mainnet or testnet?
NETWORK = 'mainnet'

EBS_SIZE = 200

# array to store list of ip files to download from github
ip_file_array = []

# a dict to store ips per region
dict_region_ip_array = {}

# a dict to store vol-id per region
dict_region_volid_array = {}

load_dotenv()
GIT_TOKEN = os.getenv('GIT_TOKEN')

profile_array = ['default', 'mainnet-aw']

def create_ip_file_array(network):
    if network == 'mainnet':
        path_mainnet_github = 'https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/'
        #path_s0 = path_mainnet_github + 'shard0.txt'
        path_s1 = path_mainnet_github + 'shard1.txt'
        path_s2 = path_mainnet_github + 'shard2.txt'
        path_s3 = path_mainnet_github + 'shard3.txt'
        return [path_s1, path_s2, path_s3]
    elif network == 'testnet':
        path_testnet_github = 'https://raw.githubusercontent.com/harmony-one/nodedb/master/testnet/'
        #path_s0 = path_testnet_github + 'shard0.txt'
        path_s1 = path_testnet_github + 'shard1.txt'
        path_s2 = path_testnet_github + 'shard2.txt'
        return [path_s1, path_s2]

def shcmd(cmd, ignore_error=False):
    ret = subprocess.call(cmd, shell=True)
    if ignore_error == False and ret != 0:
        raise RuntimeError("Failed to execute {}. Return code:{}".format(
            cmd, ret))
    return ret

def shcmd2(cmd, ignore_error=False):
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = proc.stdout.read()
    output_string = output.decode("utf-8")
    return output_string

def download_ipfiles_github(ip_array):
    for file in ip_array:
        cmd = "curl -H 'Authorization: token {token}' "\
              "-H 'Accept: application/vnd.github.v3.raw' -O "\
              "{path}".format(token=GIT_TOKEN, path=file)
        shcmd(cmd)

def create_array_to_keep_all_ip():
    all_ip = []
    current_dir = os.path.dirname(os.path.realpath(__file__))
    # TO-DO: mainnet only
    local_shard_file_array = [current_dir+"/shard1.txt", current_dir+"/shard2.txt", current_dir+"/shard3.txt"]
    print(local_shard_file_array)
    for item in local_shard_file_array:
        fp = open(item)
        line = fp.readline()
        while line:
            line = line.rstrip()
            all_ip.append(line)
            line = fp.readline()
        fp.close()
    return all_ip

def get_region_from_public_ip(ip):
    region = ''
    try:
        cmd = "host -W 20 {ip}".format(ip=ip)
        resp = shcmd2(cmd)
        info = resp.split('.')
        print(info)
        if info[-4] == 'compute':
            region = info[-5]
        elif info[-4] == 'compute-1':
            region = 'us-east-1'
        else:
            raise ValueError("cannot deduce region from name {}".format(info))
    except Exception as e:
        print("Unexpected error: %s" % e)

    return region

def create_ip_dict_per_region(ip_array):
    dict_region_ip = {}
    for ip in ip_array:
        time.sleep(2)
        region = get_region_from_public_ip(ip)
        if region not in dict_region_ip.keys():
            dict_region_ip[region] = [ip]
        else:
            dict_region_ip[region].append(ip)

    return dict_region_ip

def update_dict_region_ips(reg, ips, dict_region_volid_array):

    # our nodes are located in two different AWS accounts
    # legacy nodes are located in aws-6565 account; while tf nodes are located in aws-7746 account
    #
    for profile in profile_array:
        print("The PROFILE is: ", profile)
        session = boto3.Session(profile_name=profile)

        ec2 = session.client('ec2', region_name = reg)
        for ip in ips:
            try:
                resp = ec2.describe_instances(Filters=[{'Name': 'ip-address', 'Values': [ip]}])
                print(resp)
                if len(resp["Reservations"]) != 0:
                    vol_id = resp["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0]["Ebs"]["VolumeId"]
                    if reg not in dict_region_volid_array.keys():
                        dict_region_volid_array[reg] = [vol_id]
                    else:
                        dict_region_volid_array[reg].append(vol_id)
            except ClientError as e:
                print("Unexpected error: %s" % e)


def create_volid_dict_per_region(dict_region_ips):
    for region, ip_array in dict_region_ips.items():
        print("region - fetch vol id: ", region)
        update_dict_region_ips(region, ip_array, dict_region_volid_array)


def extend_ebs_per_region(reg, vols):
        for profile in profile_array:
            session = boto3.Session(profile_name=profile)

            ec2 = session.client('ec2', region_name = reg)
            for vol_id in vols:
                try:
                    resp = ec2.modify_volume(VolumeId = vol_id, Size = EBS_SIZE)
                    print(resp)
                except ClientError as e:
                    print("Unexpected error: %s" % e)

def extend_ebs_volumes(dict_region_volid):
    for region, volid_array in dict_region_volid.items():
        print("region - extend ebs vol: ", region)
        extend_ebs_per_region(region, volid_array)

def main():

    # # create an array to store the path to download ip files
    # ip_file_array = create_ip_file_array(NETWORK)
    #
    # # download ip files from github
    # download_ipfiles_github(ip_file_array)

    # load all ip files into a single array
    array_total_ip = create_array_to_keep_all_ip()

    # create a dict to store ip per region
    dict_region_ip_array = create_ip_dict_per_region(array_total_ip)
    print("-- dict_region_ip_array")
    pprint.pprint(dict_region_ip_array)

    # create a dict to store vol_id per region
    create_volid_dict_per_region(dict_region_ip_array)
    print("-- dict_region_volid_array")
    print(len(dict_region_volid_array))
    pprint.pprint(dict_region_volid_array)

    # aws api call to increase storage volume
    extend_ebs_volumes(dict_region_volid_array)

if __name__ == "__main__":
    main()
