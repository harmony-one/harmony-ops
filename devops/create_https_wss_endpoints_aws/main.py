#!/usr/bin/env python3

'''

PURPOSE:

create https/wss endpoints for a network

USUAGE:

$ python3 main.py <network_name>

for example, the following cmd is used to create endpoints for testnet
$ python3 main.py -n testnet


'''

import sys
import json
import os
import argparse
import boto3
from time import sleep
import subprocess
from dotenv import load_dotenv
from timeit import default_timer as timer
from datetime import timedelta

ap = argparse.ArgumentParser(description='parse the network type')
ap.add_argument("-n", required=True, help="define network type")
args = vars(ap.parse_args())

current_work_path = os.path.dirname(os.path.realpath(__file__))
network_config = current_work_path + '/' + args['n'] + '.json'






def parse_network_config(param):
    """ load the network configuration file, retrieve the value by its key """
    with open(network_config, 'r') as f:
        network_config_dict = json.load(f)

    return network_config_dict[param]




# print(parse_network_config("explorers"))

def create_endpoints_new_network():
    pass


def shcmd2(cmd, ignore_error=False):
    """ customized version of shcmd created by aw """
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, shell=True)
    output = proc.stdout.read()
    output_string = output.decode("utf-8")
    return output_string

def retrieve_instance_region(ip):
    """ deduce instance region from its ipv4 """
    cmd = "host {ip}".format(ip=ip)
    resp = shcmd2(cmd)
    info = resp.split('.')
    if info[-4] ==  'compute':
        region = info[-5]
    elif info[-4] == 'compute-1':
        region = 'us-east-1'
    else:
        raise ValueError("cannot deduce region from name {}".format(info))
    return region


def retrieve_instance_id(array_instance_ip):
    """ mapping from instance-ip -> instance-id """
    array_instance_id = []
    for ip in array_instance_ip:
        region = retrieve_instance_region(ip)
        ec2_client = boto3.client('ec2', region_name=region)
        response = ec2_client.describe_instances(Filters=[{'Name': 'ip-address', 'Values': [ip]}])
        instance_id = response["Reservations"][0]["Instances"][0]["InstanceId"]
        array_instance_id.append(instance_id)

    return array_instance_id

def update_target_groups():
    """  """

    num_of_shards = parse_network_config("num_of_shards")

    # add instance_id into an array for each shard
    for i in range(num_of_shards):
        key_explorer = "explorers_" + str(i)
        array_instance_ip = parse_network_config(key_explorer)
        array_instance_id = retrieve_instance_id(array_instance_ip)
        print(array_instance_id)

    # deregister any previous instances from the target group
    for i in range(num_of_shards):
        key_tg = "tg_s" + str(i)
        array_target_group = parse_network_config(key_tg)
        print(array_target_group)



def main():
    """  """



    # create the complete pipeline of https/wss endpoints
    # need to comment out the following func `update_target_groups()`
    create_endpoints_new_network()

    # updated target groups only, assuming other services have been created and configured
    # need to comment out the above func `create_endpoints_new_network()`
    update_target_groups()


if __name__ == "__main__":
    main()
