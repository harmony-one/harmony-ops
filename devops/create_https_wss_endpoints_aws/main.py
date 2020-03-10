#!/usr/bin/env python3

'''

PURPOSE:

create https/wss endpoints for a network on AWS

USUAGE:

$ python3 main.py <network_name>

for example, the following cmd is used to create https/wss endpoints for testnet

# build complete pipeline
$ python3 main.py -n testnet

# update endpoints only - after a network has been hard reset
$ python3 main.py -n testnet --update
or
$ python3 main.py -n testnet -u


VERSION
Mar 6, 2020     add a param on CLI to update endpoints only

'''

import sys
import json
import os
import argparse
from collections import defaultdict
import boto3
import pprint
from time import sleep
from dotenv import load_dotenv
from timeit import default_timer as timer
from datetime import timedelta

from helpers import *
from creation_certificates import *
from creation_tg import *
from creation_elb2 import *
from creation_listener import *

pp = pprint.PrettyPrinter(indent=4)



# TO-DO: create the following dicts for each region
# store target group arn, key: tg, value: arn of tg
dict_tg_arn = dict()
# store PREVIOUS instance id, key: tg, value: array of instance id
dict_tg_instanceid = defaultdict(list)

# store name of target group, key: tg_https, tg_wss, value: array of target group
dict_tg_https_wss = defaultdict(list)


NUM_OF_SHARDS = parse_network_config("num_of_shards")
# ARRAY_OF_REGIONS = parse_network_config("regions")
# TO-DO: convert them to a dict
# ARRAY_OF_VPC = parse_network_config("region_vpc")
# ARRAY_OF_WS_ENDPOINTS = parse_network_config("ws_endpoints")

BASE_DOMAIN_NAME = parse_network_config("domain_name")
ID_DOMAIN_NAME = BASE_DOMAIN_NAME.split('.')[0]
# array_domain_name       = []




def create_endpoints_new_network():
    """
    COMPLETE PIPELINE
    * 0/ - define regions for each endpoint
    * 1/ - create SSL certificates (https, and wss) on each region
    * 2/ - create Target Groups on each region
    * 3/ - create ELB
    * 4/ - create listener
    # TO-DO
    * 5/ - create entries on Route53
    """

    for i in range(NUM_OF_SHARDS):
        key_explorer = "explorers_" + str(i)
        array_instance_ip = parse_network_config(key_explorer)

        # 0/5 - detect region of explorers
        reg = retrieve_instance_region(array_instance_ip[0])
        # all nodes registered for the same endpoints should be located in the same region, if not, gracefully exit
        # verify_nodes_same_region(reg, array_instance_ip)

        print("\n################################## Creating complete pipeline for shard", str(i), " in AWS region: ", reg, "##################################\n")
        # 1/5 - request certificates
        domain_name = 'api.s' + str(i) + "." + BASE_DOMAIN_NAME
        request_ssl_certificates(reg, domain_name)
        pp.pprint(dict_region_sslcerts)

        print("\nRESULTS OF STEP 1 \n")
        pp.pprint(dict_region_sslcerts)

        # 2/5 - create target group
        array_tgs = create_name_target_group(i, ID_DOMAIN_NAME)
        pp.pprint(array_tgs)
        create_target_group(reg, array_tgs)
        pp.pprint(dict_region_tgarn)

        # 3/5 - create elb
        elb2_name = 's' + str(i) + '-' + ID_DOMAIN_NAME + '-' + reg
        create_elb2(reg, elb2_name)
        pp.pprint(dict_region_elb2arn)

        # 4/5 - create listener
        create_listener(reg, dict_region_elb2arn, dict_region_sslcerts, dict_region_tgarn)

        # 5/5 - create rule the current listener
        # test result: passed
        # create_rule()

        # 6/ - register explorer instances into the target group
        # register_explorers()


def register_explorers():
    """
    register explorer nodes into the corresponding target group
        * register the same target into tg-https and tg-wss
    depends on:
        * dict_region_tgarn
        *
    """
    for i in range(len(ARRAY_OF_REGIONS)):
        region = ARRAY_OF_REGIONS[i]
        for j in range(NUM_OF_SHARDS):
            elbv2_client = boto3.client('elbv2', region_name=region)
            array_of_exp_shard = parse_network_config(region + '-exp-' + str(j))
            array_instance_id_exp = retrieve_instance_id(array_of_exp_shard)
            # REGISTER each instance_id into the TWO target groups
            for instance in array_instance_id_exp:
                try:
                    # register targets into tg-s[i]-api-pga-https
                    resp = elbv2_client.register_targets(
                        TargetGroupArn=dict_region_tgarn[region][j],
                        Targets=[
                            {
                                'Id': instance,
                                'Port': 9500,
                            },
                        ]
                    )
                    # register targets into tg-s[i]-api-pga-wss
                    resp2 = elbv2_client.register_targets(
                        TargetGroupArn=dict_region_tgarn[region][j + NUM_OF_SHARDS],
                        Targets=[
                            {
                                'Id': instance,
                                'Port': 9800,
                            },
                        ]
                    )
                    print(
                        "--registering an explorer node into TWO target groups (tg-https and tg-wss) in region " + region)
                    sleep(4)
                except Exception as e:
                    print("Unexpected error to create the listener: %s" % e)


def create_rule():
    """


    """
    print("\n==== step 5: creating a customized rule such that traffic will be forwarded to tg-s[i]-api-pga-wss "
          "when host is ws.s[i].pga.hmny.io \n")
    # deliberately use index instead of obj to retrieve array item, this index needs to be reused to retrieve
    for i in range(len(ARRAY_OF_REGIONS)):
        region = ARRAY_OF_REGIONS[i]
        for j in range(NUM_OF_SHARDS):
            elbv2_client = boto3.client('elbv2', region_name=region)
            try:
                resp = elbv2_client.create_rule(
                    ListenerArn=dict_region_ListenerArn[region][j],
                    Conditions=[
                        {
                            'Field': 'host-header',
                            'Values': [
                                ARRAY_OF_WS_ENDPOINTS[j],
                            ],
                        },
                    ],
                    Priority=1,
                    Actions=[
                        {
                            'Type': 'forward',
                            'TargetGroupArn': dict_region_tgarn[region][j + NUM_OF_SHARDS],
                            'ForwardConfig': {
                                'TargetGroups': [
                                    {
                                        'TargetGroupArn': dict_region_tgarn[region][j + NUM_OF_SHARDS],
                                        'Weight': 1
                                    },
                                ],
                                'TargetGroupStickinessConfig': {
                                    'Enabled': False,
                                    'DurationSeconds': 1
                                }
                            }
                        },
                    ]
                )
                print("--creating a customized elb2 rule in region " + region + " for LoadBalancerArn: " +
                      dict_region_elb2arn[region][i])
                sleep(4)
            except Exception as e:
                print("Unexpected error to create the listener: %s" % e)





def create_dict_tg():
    """
    * number of tg in each region = number of shards X 2 (one for https, and one for wss)
    * the names of tgs are identical in each region
    * the config for each tg (https and wss) are different, need to group them in this dict
    """
    for i in range(NUM_OF_SHARDS):
        key_tg = "tg_s" + str(i)
        array_target_group = parse_network_config(key_tg)
        dict_tg_https_wss["tg_https"].append(array_target_group[0])
        dict_tg_https_wss["tg_wss"].append(array_target_group[1])





def update_target_groups():
    """
    DEREGISTER any previous instances from the target group given the existing target groups
    * 1/3 - find target group arn `aws elbv2 describe-target-groups --name "tg-s0-api-pga-https"`
    * 2/3 - find all the instances belonging to a specific target group `aws elbv2 describe-target-health --target-group-arn <arn>` 
    * 3/3 - deregister all instances `deregister_targets`
    """

    # detect which region the explorer(s) are located
    for j in range(NUM_OF_SHARDS):
        key_explorer = "explorers_" + str(j)
        array_instance_ip = parse_network_config(key_explorer)

        reg = retrieve_instance_region(array_instance_ip[0])
        # all nodes registered for the same endpoints should be located in the same region, if not, exit
        verify_nodes_same_region(reg, array_instance_ip)

        elbv2_client = boto3.client('elbv2', region_name=reg)

        array_target_group = create_name_target_group(j, ID_DOMAIN_NAME)
        pp.pprint(array_target_group)

        # # 1/3 - retrieve target group arn
        # for tg in array_target_group:
        #     resp = elbv2_client.describe_target_groups(Names=[tg])
        #     tg_arn = resp["TargetGroups"][0]["TargetGroupArn"]
        #     dict_tg_arn[tg] = tg_arn



    # region='us-east-1'
    # elbv2_client = boto3.client('elbv2', region_name=region)
    #
    # for j in range(NUM_OF_SHARDS):
    #
    #     key_tg = "tg_s" + str(j)
    #     array_target_group = parse_network_config(key_tg)
    #     # ['tg-s0-api-pga-https-test', 'tg-s0-api-pga-wss-test']
    #
    #     # 1/3 - retrieve target group arn
    #     for tg in array_target_group:
    #         resp = elbv2_client.describe_target_groups(Names=[tg])
    #         tg_arn = resp["TargetGroups"][0]["TargetGroupArn"]
    #         dict_tg_arn[tg] = tg_arn
    #
    #     # 2/3 - find all the instances
    #     for tg in array_target_group:
    #         resp = elbv2_client.describe_target_health(TargetGroupArn=dict_tg_arn[tg])
    #         num_of_targets = len(resp["TargetHealthDescriptions"])
    #         for k in range(num_of_targets):
    #             instance_id = resp["TargetHealthDescriptions"][k]["Target"]["Id"]
    #             dict_tg_instanceid[tg].append(instance_id)
    #
    #     pp.pprint(dict_tg_instanceid)
    #
    #     # 3/3 - deregister all instances, then we can have a clean and nice target group
    #     for tg in array_target_group:
    #         for instance_id in dict_tg_instanceid[tg]:
    #             resp = elbv2_client.deregister_targets(TargetGroupArn=dict_tg_arn[tg], Targets=[{'Id': instance_id}])
    #
    # """
    # REGISTER instances (array_instance_id) into the target group (array_target_group)
    # """
    # for k in range(NUM_OF_SHARDS):
    #     key_explorer = "explorers_" + str(k)
    #     array_instance_ip = parse_network_config(key_explorer)
    #     array_instance_id = retrieve_instance_id(array_instance_ip)
    #
    #     key_tg = "tg_s" + str(k)
    #     array_target_group = parse_network_config(key_tg)
    #
    #     # outer for loop: loop through 2 tg, https and wss
    #     # inner loop: add every single instance id into each tg
    #     for m in range(len(array_target_group)):
    #         for instance in array_instance_id:
    #             response = elbv2_client.register_targets(
    #                     TargetGroupArn=dict_tg_arn[array_target_group[m]],
    #                     Targets=[{'Id': instance,},]
    #             )


def main():
    # update targets registered to the endpoints
    if args.update:
        update_target_groups()
        sys.exit(0)

    # create the complete pipeline of https/wss endpoints
    create_endpoints_new_network()


if __name__ == "__main__":
    main()
