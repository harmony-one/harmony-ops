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




print(parse_network_config("explorers"))

def create_endpoints_new_network():
    pass


def retrieve_instance_id(array_instance_ip):
    """ mapping from instance ip -> instance-id """
    pass


def update_target_groups():
    """  """
    array_instance_ip = parse_network_config("explorers")
    array_instance_id = retrieve_instance_id(array_instance_ip)

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
