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


NUM_OF_SHARDS           = parse_network_config("num_of_shards")
ARRAY_OF_REGIONS        = parse_network_config("regions")
ARRAY_OF_VPC            = parse_network_config("region_vpc")
ARRAY_OF_WS_ENDPOINTS   = parse_network_config("ws_endpoints")

BASE_DOMAIN_NAME        = parse_network_config("domain_name")
ID_DOMAIN_NAME          = BASE_DOMAIN_NAME.split('.')[0]
array_domain_name       = []

#### CREATE A COMPLETE PIPELINE ####
dict_region_elb2arn     = defaultdict(list)
dict_region_sslcerts    = defaultdict(list)
dict_region_tgarn       = defaultdict(list)
dict_region_ListenerArn = defaultdict(list)


def create_endpoints_new_network():
    """
    COMPLETE PIPELINE
    * 1/ - create SSL certificates (https, and wss) on each region
    * 2/ - create Target Groups on each region
    * 3/ - create ELB
    * 4/ - create listener

    * / - create entries on Route53
    """

    # 1/4 - request certificates
    # test result: passed
    request_ssl_certificates()

    # 2/4 - create tg on each region
    # test result: passed
    create_target_group()

    # 3/4 - create elb
    # test result: passed
    create_elb2()

    # 4/ - create listener
    # test result: passed
    create_listener()

    # 5/ - create rule the current listener
    # test result: passed
    create_rule()

    # 6/ - register explorer instances into the target group
    register_explorers()


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
            array_of_exp_shard = parse_network_config(region+'-exp-'+str(j))
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
                        TargetGroupArn=dict_region_tgarn[region][j+NUM_OF_SHARDS],
                        Targets=[
                            {
                                'Id': instance,
                                'Port': 9800,
                            },
                        ]
                    )
                    print("--registering an explorer node into TWO target groups (tg-https and tg-wss) in region " + region)
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
                            'TargetGroupArn': dict_region_tgarn[region][j+NUM_OF_SHARDS],
                            'ForwardConfig': {
                                'TargetGroups': [
                                    {
                                        'TargetGroupArn': dict_region_tgarn[region][j+NUM_OF_SHARDS],
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
                print("--creating a customized elb2 rule in region " + region + " for LoadBalancerArn: " + dict_region_elb2arn[region][i])
                sleep(4)
            except Exception as e:
                print("Unexpected error to create the listener: %s" % e)



def create_listener():
    """
    depends on:
        * dict_region_elb2arn
        * dict_region_sslcerts
        * dict_region_tgarn
    *
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
                print("--creating https listener with attaching ssl certificat in region " + region + ", LoadBalancerArn: " + dict_region_elb2arn[region][i])
                sleep(4)
        except Exception as e:
            print("Unexpected error to create the listener: %s" % e)

    pp.pprint(dict_region_ListenerArn)


def create_elb2():
    """
    numbers of elb2 in each region = number of shards

    """
    print("\n==== step 3: creating elb2, LoadBalancerArn will be stored into dict_region_elb2arn \n")

    for region in ARRAY_OF_REGIONS:
        elbv2_client = boto3.client('elbv2', region_name=region)
        # need to create $NUM_OF_SHARDS elb2  in each region
        for i in range(NUM_OF_SHARDS):
            elb2_name = 's' + str(i) + '-' + ID_DOMAIN_NAME + '-' + region
            try:
                pass
                resp = elbv2_client.create_load_balancer(
                    Name=elb2_name,
                    Subnets=parse_network_config('subnet_' + region),
                    SecurityGroups=parse_network_config('sg_' + region),
                    Scheme='internet-facing',
                    Type='application',
                    IpAddressType='ipv4'
                )
                dict_region_elb2arn[region].append(resp['LoadBalancers'][0]['LoadBalancerArn'])
                print("--creating Elastic/Application Load Balancer in region " + region + ", elb name: " + elb2_name)
                sleep(4)
            except Exception as e:
                print("Unexpected error to create the elb2: %s" % e)

    pp.pprint(dict_region_elb2arn)


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


def create_target_group():

    create_dict_tg()

    print("\n==== step 2: creating target group in each region, TargetGroupArn will be stored into dict_region_tgarn \n")
    # deliberately use index instead of obj to retrieve array item, this index needs to be reused to retrieve VpcId
    for i in range(len(ARRAY_OF_REGIONS)):
        region = ARRAY_OF_REGIONS[i]
        elbv2_client = boto3.client('elbv2', region_name=ARRAY_OF_REGIONS[i])
        for tg_name in ["tg_https", "tg_wss"]:
            if tg_name == "tg_https":
                for name in dict_tg_https_wss[tg_name]:
                    try:
                        resp = elbv2_client.create_target_group(
                            Name=name,
                            Protocol='HTTP',
                            Port=9500,
                            VpcId=ARRAY_OF_VPC[i],
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
                        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
                        print("--creating target group in region " + region + ", target group name: " + name)
                        sleep(2)
                    except Exception as e:
                        print("Unexpected error to create the target group: %s" % e)
            if tg_name == "tg_wss":
                for name in dict_tg_https_wss[tg_name]:
                    try:
                        resp = elbv2_client.create_target_group(
                            Name=name,
                            Protocol='HTTP',
                            Port=9800,
                            VpcId=ARRAY_OF_VPC[i],
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
                        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
                        print("--creating target group in region " + region + ", target group name: " + name)
                        sleep(4)
                    except Exception as e:
                        print("Unexpected error to create the target group: %s" % e)

    pp.pprint(dict_region_tgarn)

def request_ssl_certificates():
    """
    number of ssl certificates per region = NUM_OF_SHARDS * 2 (HTTPS and WSS)
    * idempotent ops
    * store CertificateArn to dict_region_sslcerts
    """
    create_domain_name()

    print("\n==== step 1: request SSL certificates in each region, CertificateArn will be stored into dict_region_sslcerts \n")
    for region in ARRAY_OF_REGIONS:
        acm_client = boto3.client(service_name='acm', region_name=region)
        for dn in array_domain_name:
            try:
                resp = acm_client.request_certificate(
                        DomainName = dn,
                        ValidationMethod = 'DNS',
                )
                dict_region_sslcerts[region].append(resp['CertificateArn'])
                print("--creating ssl certificate in region " + region + " for domain name " + dn)
                print(dn + ': ' + resp['CertificateArn'])
                sleep(1)
            except Exception as e:
                print("Unexpected error to request certificates: %s" % e)

    pp.pprint(dict_region_sslcerts)

def create_domain_name():
    """
    for each region, there should be 2 X NUM_OF_SHARDS domain names
    for instance:
        s0: api.s0.pga.hmny.io and ws.s0.pga.hmny.io
    """
    for prefix in ["api.s"]:
        for i in range(NUM_OF_SHARDS):
            array_domain_name.append(prefix + str(i) + "." + BASE_DOMAIN_NAME)







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
