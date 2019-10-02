#!/usr/bin/env python

import sys
import os
import boto3
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

dict_subnetid = {}

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
            subnet_array = ['subnet-2f00cb73', 'subnet-7da3751a' ]
            try:
                resp_create_alb = client.create_load_balancer(Name = alb_name,
                                                Subnets = subnetid_dict[region],
                                                Scheme = 'internet-facing',
                                                Type='application',
                                                IpAddressType='ipv4'
                )
            except Exception as e:
                print("Unexpected error: %s" % e)

    # client = boto3.client(service_name = 'elbv2', region_name = 'us-east-1')
    # resp = client.create_load_balancer(Name = 'test-ALB')




def main():

    region_array    = create_region_array(NETWORK)

    shard_array     = create_shard_array(NETWORK) 

    subnetid_dict   = create_subnet_array(vpc_array, region_array)

    create_load_balancer(region_array, shard_array, subnetid_dict)

    alb_arn_array   = create_alb_arn_array() 

    return 0

if __name__ == "__main__":
    main()












