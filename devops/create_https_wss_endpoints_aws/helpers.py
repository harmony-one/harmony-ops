import argparse
import os
import subprocess
import sys
import boto3
import json


ap = argparse.ArgumentParser(description='parse the network type')
# param to define network, required
ap.add_argument("-n", action="store", dest='network_value', required=True, help="define network type")
# param to check if update endpoints needed, optional
ap.add_argument('-u', '--update', action="store_true", help="update targets for the endpoints only", default=False)
args = ap.parse_args()

current_work_path = os.path.dirname(os.path.realpath(__file__))
if args.network_value:
    network_config = current_work_path + '/' + args.network_value + '.json'


def parse_network_config(param):
    """ load the network configuration file, retrieve the value by its key """
    with open(network_config, 'r') as f:
        network_config_dict = json.load(f)

    return network_config_dict[param]

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


def verify_nodes_same_region(region, array_ip):
    for ip in array_ip:
        if retrieve_instance_region(ip) != region:
            sys.exit("All nodes registered for the same endpoints should be located in the region, if not, gracefully exit!! ")


def create_name_target_group(shard, id_domain):
    ret = []
    tg_prefix = 'tg-s' + str(shard) + '-api-' + id_domain + '-'
    ret.append(tg_prefix+'https')
    ret.append(tg_prefix+'wss')
    return ret


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
