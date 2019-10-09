#!/usr/bin/env python

import sys
import os
import boto3
from time import sleep
import subprocess
from dotenv import load_dotenv
'''
PURPOSE

create HTTPS and WSS endpoints for testnet, Pangaea, and Mainnet

DESCRPTION

Take mainnet as an example, we need to create an ALB for each shard in each 
region, 8 regions in total. And for each ALB, we need to request two 
certificates for each endpints. And we also need to create two TG for each ALB.

So for reach region, we need to create

ALB             X 4
Certificates    X 8
Target Group    X 8

Then add the 5 instances into each Target Group.

We will have a very similar infrastructure for Pangaea network and testnet.

PLAN

* Create Load Balancer
* Create Target Groups
* Create Listeners to link Target Groups to the ELB
* Register instances to Target Groups

'''

# t -> mainnet
# b -> testnet, aka, betanet
# p -> pangaea 

NETWORK = 't'

vpc_array = ['vpc-88c9c2f3',
             'vpc-2c420a44',
             'vpc-bb770fdc',
             'vpc-cd3e33b4',
             'vpc-dd631cba',
             'vpc-864103e1',
             'vpc-94246aff',
             'vpc-80166ce6']

group_name_alb = 'wide-open'
sg_alb_array = []

dict_subnetid = {}

dict_alb_name = {}

dict_alb_arn = {}

dict_domainname_networks = {}


if NETWORK == 't':
    path_mainnet_github = 'https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/'
    path_shard0 = path_mainnet_github + 'shard0lg.txt'
    path_shard1 = path_mainnet_github + 'shard1.txt'
    path_shard2 = path_mainnet_github + 'shard2.txt'
    path_shard3 = path_mainnet_github + 'shard3.txt'
    print(path_shard0)
elif NETWORK == 'p':
    #TO-DO
    pass
elif NETWORK == 'b':
    #TO-DO
    pass
else:
    print("NETWORK ID is not defined.")

GIT_TOKEN = os.getenv("GIT_TOKEN")
print("GIT_TOKEN: ", GIT_TOKEN)


def create_region_array(network_id):
    # mainnet
    if network_id == 't':
        return [ 'us-east-1']
    # pangaea
    elif network_id == 'p':
        return [ 'us-east-1', 'us-east-2']
    # betanet or testnet
    elif network_id == 'b':
        return [ 'us-east-1', 'us-east-2']

def create_shard_array(network_id):
    # mainnet
    if network_id == 't':
        return [ 't-s0', 't-s1', 't-s2', 't-s3' ]
    # pangaea
    elif network_id == 'p':
        return [ 'p-s0', 'p-s1', 'p-s2', 'p-s3' ]
    # betanet or testnet
    elif network_id == 'b':
        return [ 'b-s0', 'b-s1' ]

def create_subnet_array(vpc_array, region_array):
    for ind in range(len(region_array)):
        client = boto3.client(service_name = 'ec2', region_name = region_array[ind])
        subnets = client.describe_subnets(Filters=[{'Name' : 'vpc-id', 
                                'Values' : [vpc_array[ind]]}]).get('Subnets')
        for indx in range(len(subnets)):
            if region_array[ind] not in dict_subnetid.keys():
                dict_subnetid[region_array[ind]] = [subnets[indx].get('SubnetId')]
            else:
                 dict_subnetid[region_array[ind]].append(subnets[indx].get('SubnetId'))
            
    return dict_subnetid

def create_load_balancer(region_array, shard_array, subnetid_dict):
    for region in region_array:
        client = boto3.client(service_name = 'elbv2', region_name = region)

        for shard in shard_array:
            alb_name = shard + '-https-wss-' + region
            if region not in dict_alb_name.keys():
                dict_alb_name[region] = [alb_name]
            else:
                dict_alb_name[region].append(alb_name)
            try:
                resp_create_alb = client.create_load_balancer(Name = alb_name,
                                                Subnets = subnetid_dict[region],
                                                Scheme = 'internet-facing',
                                                Type='application',
                                                IpAddressType='ipv4'
                )
            except Exception as e:
                print("Unexpected error: %s" % e)

def create_alb_arn_dict(region_array):
    for region in region_array:
        try:
            client = boto3.client(service_name = 'elbv2', region_name = region)
            for alb_name in dict_alb_name[region]:
                arn = client.describe_load_balancers(
                    Names=[alb_name]).get('LoadBalancers')[0].get('LoadBalancerArn')
                if region not in dict_alb_arn.keys():
                    dict_alb_arn[region] = [arn]
                else:
                    dict_alb_arn[region].append(arn)
        except Exception as e:
                print("Unexpected error - create alb arn dict: %s" % e)

def create_wide_open_sg_array(region_array):
    for region in region_array:
        try:
            client = boto3.client(service_name = 'ec2', region_name = region)
            resp = client.describe_security_groups(
                Filters = [
                    {'Name' : 'group-name', 'Values' : [group_name_alb]} 
                ]
            )
            group_id = resp['SecurityGroups'][0]['GroupId']
            sg_alb_array.append(group_id)
        except Exception as e:
                print("Unexpected error - create wide open sg array: %s" % e)
    return sg_alb_array

def set_security_group_alb(region_array, dict_alb_arn):
    for region in region_array:
        try:
            client = boto3.client(service_name = 'elbv2', region_name = region)
            for arn in dict_alb_arn[region]:
                client.set_security_groups(
                    LoadBalancerArn = arn,
                    SecurityGroups=[
                        'sg-0a9f239987978e0eb',
                    ]  
                )
        except Exception as e:
                print("Unexpected error - set sg of alb: %s" % e)

def create_domainnames_networks():
    network_array = ['b', 'p', 't']

    
    for network in network_array:
        if network == 'b':
            shard_array = ['s0', 's1']
            for shard in shard_array:
                full_domainname_api = 'api.' + shard + '.' + network + '.hmny.io'
                full_domainname_wss = 'ws.'  + shard + '.' + network + '.hmny.io'
                if network not in dict_domainname_networks.keys():
                    dict_domainname_networks[network] = [full_domainname_api]
                    dict_domainname_networks[network].append(full_domainname_wss)
                else:
                    dict_domainname_networks[network].append(full_domainname_api)
                    dict_domainname_networks[network].append(full_domainname_wss)
        else:
            shard_array = ['s0', 's1', 's2', 's3']
            for shard in shard_array:
                full_domainname_api = 'api.' + shard + '.' + network + '.hmny.io'
                full_domainname_wss = 'ws.'  + shard + '.' + network + '.hmny.io'
                if network not in dict_domainname_networks.keys():
                    dict_domainname_networks[network] = [full_domainname_api]
                    dict_domainname_networks[network].append(full_domainname_wss)
                else:
                    dict_domainname_networks[network].append(full_domainname_api)
                    dict_domainname_networks[network].append(full_domainname_wss)

    return dict_domainname_networks

def request_ssl_certificates(region_array, dict_domainname_networks):
    domainname_array = []
    for item in dict_domainname_networks.values():
        domainname_array += item

    for region in region_array:
        try:
            client = boto3.client(service_name = 'acm', region_name = region)
            for domain in domainname_array:
                response = client.request_certificate(
                    DomainName = domain,
                    ValidationMethod = 'DNS',
                )
        except Exception as e:
             print("Unexpected error: %s" % e)     

def shcmd(cmd, ignore_error=False):
    print('Doing:', cmd)
    ret = subprocess.call(cmd, shell=True)
    print('Returned', ret, cmd)
    if ignore_error == False and ret != 0:
        raise RuntimeError("Failed to execute {}. Return code:{}".format(
            cmd, ret))
    return ret

def download_ip_list_from_github():

    # download list of IP from shard 0
    cmd = "curl -H 'Authorization: token {token}' "\
        "-H 'Accept: application/vnd.github.v3.raw' -o shard0.txt "\
        "{path}".format(token=GIT_TOKEN, path=path_shard0)
    shcmd(cmd)

    # download list of IP from shard 1
    cmd = "curl -H 'Authorization: token {token}' "\
        "-H 'Accept: application/vnd.github.v3.raw' -o shard1.txt "\
        "{path}".format(token=GIT_TOKEN, path=path_shard1)
    shcmd(cmd)

        # download list of IP from shard 2
    cmd = "curl -H 'Authorization: token {token}' "\
        "-H 'Accept: application/vnd.github.v3.raw' -o shard2.txt "\
        "{path}".format(token=GIT_TOKEN, path=path_shard2)
    shcmd(cmd)

        # download list of IP from shard 3
    cmd = "curl -H 'Authorization: token {token}' "\
        "-H 'Accept: application/vnd.github.v3.raw' -o shard3.txt "\
        "{path}".format(token=GIT_TOKEN, path=path_shard3)
    shcmd(cmd)      

def main():

    region_array    = create_region_array(NETWORK)

    shard_array     = create_shard_array(NETWORK) 

    subnetid_dict   = create_subnet_array(vpc_array, region_array)

    create_load_balancer(region_array, shard_array, subnetid_dict)

    create_alb_arn_dict(region_array) 

    wide_open_sg_array = create_wide_open_sg_array(region_array)

    set_security_group_alb(region_array, dict_alb_arn)
    
    # one-time-use independent funcs
    dict_domainname_networks = create_domainnames_networks()
    request_ssl_certificates(region_array, dict_domainname_networks)

    # download list of (legacy) IP from github
    download_ip_list_from_github()


    return 0

if __name__ == "__main__":
    main()












