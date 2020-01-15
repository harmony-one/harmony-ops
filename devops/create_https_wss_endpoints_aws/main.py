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
from collections import defaultdict

import boto3
import pprint
from time import sleep
import subprocess
from dotenv import load_dotenv
from timeit import default_timer as timer
from datetime import timedelta




pp = pprint.PrettyPrinter(indent=4)

ap = argparse.ArgumentParser(description='parse the network type')
ap.add_argument("-n", required=True, help="define network type")
args = vars(ap.parse_args())

current_work_path = os.path.dirname(os.path.realpath(__file__))
network_config = current_work_path + '/' + args['n'] + '.json'



# TO-DO: create the following dicts for each region
# store target group arn, key: tg, value: arn of tg
dict_tg_arn = dict()
# store PREVIOUS instance id, key: tg, value: array of instance id
dict_tg_instanceid = defaultdict(list)
# store CURRENT instance id, key: tg, value: array of instance id





# TO-DO: move to a helper class later
def parse_network_config(param):
    """ load the network configuration file, retrieve the value by its key """
    with open(network_config, 'r') as f:
        network_config_dict = json.load(f)

    return network_config_dict[param]


NUM_OF_REGIONS = parse_network_config("num_of_regions")
NUM_OF_SHARDS = parse_network_config("num_of_shards")
ARRAY_OF_REGIONS = parse_network_config("regions")
DOMAIN_NAME = parse_network_config("domain_name")







#### CREATE A COMPLETE PIPELINE ####
def create_endpoints_new_network():
    """
    COMPLETE PIPELINE
    * 1/4 - create SSL certificates (https, and wss) on each region
    * 2/4 - create Target Groups on each region
    * 3/4 - create ELB
    * 4/4 - create entries on Route53
    """

    # 1/4 - request certificates
    request_ssl_certificates()





def request_ssl_certificates():
    for region in ARRAY_OF_REGIONS:
        acm_client = boto3.client(service_name='acm', region_name=region)

def create_domain_name():
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



#### UPDATE TARGET GROUP ONLY ####
def update_target_groups():
    """  """

    # TO-DO: add support to mulitple regions
    region='us-west-2'
    elbv2_client = boto3.client('elbv2', region_name=region)

    """ 
    DEREGISTER any previous instances from the target group given the existing target groups
    * 1/3 - find target group arn `aws elbv2 describe-target-groups --name "tg-s0-api-pga-https"`
    * 2/3 - find all the instances belonging to a specific target group `aws elbv2 describe-target-health --target-group-arn <arn>` 
    * 3/3 - deregister all instances `deregister_targets`
    """

#    for j in range(NUM_OF_SHARDS):
    for j in range(1): # for testing only
        key_tg = "tg_s" + str(j)
        array_target_group = parse_network_config(key_tg)
        # ['tg-s0-api-pga-https-test', 'tg-s0-api-pga-wss-test']

        # 1/3 - retrieve target group arn
        for tg in array_target_group:
            resp = elbv2_client.describe_target_groups(Names=[tg])
            tg_arn = resp["TargetGroups"][0]["TargetGroupArn"]
            dict_tg_arn[tg] = tg_arn

        # 2/3 - find all the instances
        for tg in array_target_group:
            resp = elbv2_client.describe_target_health(TargetGroupArn=dict_tg_arn[tg])
            num_of_targets = len(resp["TargetHealthDescriptions"])
            for k in range(num_of_targets):
                instance_id = resp["TargetHealthDescriptions"][k]["Target"]["Id"]
                dict_tg_instanceid[tg].append(instance_id)

        pp.pprint(dict_tg_instanceid)

        # 3/3 - deregister all instances, then we can have a clean and nice target group
        for tg in array_target_group:
            for instance_id in dict_tg_instanceid[tg]:
                resp = elbv2_client.deregister_targets(TargetGroupArn=dict_tg_arn[tg], Targets=[{'Id': instance_id}])

    """ 
    REGISTER instances (array_instance_id) into the target group (array_target_group)
    """
    # for i in range(NUM_OF_SHARDS):
    for k in range(1):
        key_explorer = "explorers_" + str(k)
        array_instance_ip = parse_network_config(key_explorer)
        array_instance_id = retrieve_instance_id(array_instance_ip)

        key_tg = "tg_s" + str(k)
        array_target_group = parse_network_config(key_tg)

        # outer for loop: loop through 2 tg, https and wss
        # inner loop: add every single instance id into each tg
        for m in range(len(array_target_group)):
            for instance in array_instance_id:
                response = elbv2_client.register_targets(
                        TargetGroupArn=dict_tg_arn[array_target_group[m]],
                        Targets=[{'Id': instance,},]
                )



def main():
    """  """

    # create the complete pipeline of https/wss endpoints
    # need to comment out the following func `update_target_groups()`
    create_endpoints_new_network()

    # updated target groups only, assuming other services have been created and configured
    # need to comment out the above func `create_endpoints_new_network()`
    # update_target_groups()


if __name__ == "__main__":
    main()
