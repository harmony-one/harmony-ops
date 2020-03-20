import boto3

from helpers import *
from collections import defaultdict

dict_region_elb2arn = defaultdict(list)
region_elb2_dns_name = ""


# step 3 - create alb
def create_elb2(region, elb2_name):
    global region_elb2_dns_name

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
        # record info about elb
        dict_region_elb2arn[region].append(resp['LoadBalancers'][0]['LoadBalancerArn'])
        region_elb2_dns_name = resp['LoadBalancers'][0]['DNSName']

        print("--creating Elastic/Application Load Balancer in region " + region + ", elb name: " + elb2_name)
    except Exception as e:
        print("Unexpected error to create the elb2: %s" % e)

    # pp.pprint(dict_region_elb2arn)
