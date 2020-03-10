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

pp = pprint.PrettyPrinter(indent=4)

ap = argparse.ArgumentParser(description='parse the network type')
# param to define network, required
ap.add_argument("-n", action="store", dest='network_value', required=True, help="define network type")
# param to check if update endpoints needed, optional
ap.add_argument('-u', '--update', action="store_true", help="update targets for the endpoints only", default=False)
args = ap.parse_args()

current_work_path = os.path.dirname(os.path.realpath(__file__))
if not args.network_value:
    network_config = current_work_path + '/' + args.network_value + '.json'

# TO-DO: create the following dicts for each region
# store target group arn, key: tg, value: arn of tg
dict_tg_arn = dict()
# store PREVIOUS instance id, key: tg, value: array of instance id
dict_tg_instanceid = defaultdict(list)

# store name of target group, key: tg_https, tg_wss, value: array of target group
dict_tg_https_wss = defaultdict(list)


# TO-DO: move to a helper class later
def parse_network_config(param):
    """ load the network configuration file, retrieve the value by its key """
    with open(network_config, 'r') as f:
        network_config_dict = json.load(f)

    return network_config_dict[param]


NUM_OF_SHARDS = parse_network_config("num_of_shards")
ARRAY_OF_REGIONS = parse_network_config("regions")
# TO-DO: convert them to a dict
ARRAY_OF_VPC = parse_network_config("region_vpc")
ARRAY_OF_WS_ENDPOINTS = parse_network_config("ws_endpoints")

BASE_DOMAIN_NAME = parse_network_config("domain_name")
ID_DOMAIN_NAME = BASE_DOMAIN_NAME.split('.')[0]
# array_domain_name       = []

#### CREATE A COMPLETE PIPELINE ####
dict_region_elb2arn = defaultdict(list)
dict_region_sslcerts = defaultdict(list)
dict_region_tgarn = defaultdict(list)
dict_region_ListenerArn = defaultdict(list)

# dict for vpc id, 4 most common regions for now, need to add more if necessary
dict_vpc_id = {
    "us-east-1": "vpc-88c9c2f3",
    "us-east-2": "vpc-2c420a44",
    "us-west-1": "vpc-bb770fdc",
    "us-west-2": "vpc-cd3e33b4"
}


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

        print("\n########### Creating complete pipeline for shard", str(i), " in AWS region: ", reg, "###########\n")
        # 1/5 - request certificates
        domain_name = 'api.s' + str(i) + "." + BASE_DOMAIN_NAME
        request_ssl_certificates(reg, domain_name)

        # 2/5 - create target group
        array_tgs = create_name_target_group(i, ID_DOMAIN_NAME)
        create_target_group(reg, array_tgs)

        # 3/5 - create elb
        elb2_name = 's' + str(i) + '-' + ID_DOMAIN_NAME + '-' + reg
        create_elb2(reg, elb2_name)

        # 4/5 - create listener
        # test result: passed
        create_listener(reg)

        # 5/5 - create rule the current listener
        # test result: passed
        create_rule()

        # 6/ - register explorer instances into the target group
        register_explorers()


# step 1: request SSL certificates
def request_ssl_certificates(region, dn):
    """
    Notes:
        * idempotent ops
        * store CertificateArn to dict_region_sslcerts
    """

    print(
        "\n==== step 1: request SSL certificates in each region, CertificateArn will be stored into dict_region_sslcerts \n")
    acm_client = boto3.client(service_name='acm', region_name=region)
    try:
        resp = acm_client.request_certificate(
            DomainName=dn,
            ValidationMethod='DNS',
        )
        dict_region_sslcerts[region].append(resp['CertificateArn'])
        print("--creating ssl certificate in region " + region + " for domain name " + dn)
        print(dn + ': ' + resp['CertificateArn'])
    except Exception as e:
        print("Unexpected error to request certificates: %s" % e)

    pp.pprint(dict_region_sslcerts)


# step 2: create target group
def create_target_group(region, target_group_array):
    # to be cleaned up later
    create_dict_tg()

    print(
        "\n==== step 2: creating target group in each region, TargetGroupArn will be stored into dict_region_tgarn \n")
    elbv2_client = boto3.client('elbv2', region_name=region)

    print("Creating target group: ", target_group_array[0])
    try:
        resp = elbv2_client.create_target_group(
            Name=target_group_array[0],
            Protocol='HTTP',
            Port=9500,
            VpcId=dict_vpc_id.get(region),
            HealthCheckProtocol='HTTP',
            HealthCheckPort='traffic-port',
            HealthCheckEnabled=True,
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={
                'HttpCode': '200'
            },
            TargetType='instance'
        )
        # TO-DO:
        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
        print("--creating target group in region " + region + ", target group name: " + target_group_array[0])
    except Exception as e:
        print("Unexpected error to create the target group: %s" % e)

    print("Creating target group: ", target_group_array[1])
    try:
        resp = elbv2_client.create_target_group(
            Name=name,
            Protocol='HTTP',
            Port=9800,
            VpcId=dict_vpc_id.get(region),
            HealthCheckProtocol='HTTP',
            HealthCheckPort='traffic-port',
            HealthCheckEnabled=True,
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={
                'HttpCode': '400'
            },
            TargetType='instance'
        )
        # TO-DO:
        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
        print("--creating target group in region " + region + ", target group name: " + target_group_array[1])
    except Exception as e:
        print("Unexpected error to create the target group: %s" % e)

    # TO-DO
    pp.pprint(dict_region_tgarn)


# step 3 - create alb
def create_elb2(region, elb2_name):
    print("\n==== step 3: creating elb2, LoadBalancerArn will be stored into dict_region_elb2arn \n")
    elbv2_client = boto3.client('elbv2', region_name=region)
    try:
        resp = elbv2_client.create_load_balancer(
            Name=elb2_name,
            Subnets=parse_network_config('subnet_' + region),
            SecurityGroups=parse_network_config('sg_' + region),
            Scheme='internet-facing',
            Type='application',
            IpAddressType='ipv4'
        )
        # TO-DO:
        dict_region_elb2arn[region].append(resp['LoadBalancers'][0]['LoadBalancerArn'])
        print("--creating Elastic/Application Load Balancer in region " + region + ", elb name: " + elb2_name)
    except Exception as e:
        print("Unexpected error to create the elb2: %s" % e)

    pp.pprint(dict_region_elb2arn)

# step 4 - create listener
# not refactored yet
def create_listener():
    """
    depends on:
        * dict_region_elb2arn
        * dict_region_sslcerts
        * dict_region_tgarn
    """

    print("\n==== step 4: creating https listener on the created elb2, ListenerArn will be stored into dict_region_ListenerArn \n")
    for region in ARRAY_OF_REGIONS:
        elbv2_client = boto3.client('elbv2', region_name=region)

        try:
            for i in range(NUM_OF_SHARDS):
                resp = elbv2_client.create_listener(
                    LoadBalancerArn=dict_region_elb2arn[region][i],
                    Protocol='HTTPS',
                    Port=443,
                    SslPolicy='ELBSecurityPolicy-2016-08',
                    Certificates=[{'CertificateArn': dict_region_sslcerts[region][i]}],
                    DefaultActions=[
                        {
                            'Type': 'forward',
                            # tg-s[i]-api-pga-https
                            'TargetGroupArn': dict_region_tgarn[region][i],
                            'ForwardConfig': {
                                'TargetGroups': [
                                    {
                                        # tg-s[i]-api-pga-https
                                        'TargetGroupArn': dict_region_tgarn[region][i],
                                        'Weight': 1
                                    },
                                ],
                                'TargetGroupStickinessConfig': {
                                    'Enabled': False,
                                }
                            }
                        },
                    ]
                )
                dict_region_ListenerArn[region].append(resp['Listeners'][0]['ListenerArn'])
                print(
                    "--creating https listener with attaching ssl certificat in region " + region + ", LoadBalancerArn: " +
                    dict_region_elb2arn[region][i])
                sleep(4)
        except Exception as e:
            print("Unexpected error to create the listener: %s" % e)

    pp.pprint(dict_region_ListenerArn)

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

        # all nodes registered for the same endpoints should be located in the same region, if not, exit
        verify_nodes_same_region(array_instance_ip)

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
