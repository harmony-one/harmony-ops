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

network_config_cache = {}


def parse_network_abbr(file_path):
    global network_config_cache
    # load network config
    with open(file_path, 'r') as f:
        network_config_dict = json.load(f)
    network_config_cache = network_config_dict

    # analyze network type
    domain_name = network_config_dict['domain_name']
    domain_name_parts = domain_name.split('.')
    network_abbr = domain_name_parts[0]
    return network_abbr


def parse_distribution_config(file_path):
    """ load the distribution config file, retrieve the explorer ips """
    dict_explorer_ip = {
        "explorers_0": [],
        "explorers_1": [],
        "explorers_2": [],
        "explorers_3": [],
    }

    with open(file_path, 'r') as f:
        for line in f:
            node_info = line.split(' ')
            if node_info[2] == 'explorer_node':
                dict_explorer_ip['explorers_' + node_info[3]].append(node_info[0])
    return dict_explorer_ip


def update_network_config_explorers(file_path, dict_explorer_ip):
    for explorer_name in dict_explorer_ip.keys():
        network_config_cache[explorer_name] = dict_explorer_ip[explorer_name]

    with open(file_path, 'w') as f:
        json.dump(network_config_cache, f)


def parse_network_config(param):
    """ load the network configuration file, retrieve the value by its key """
    global network_config_cache

    # optimize configuration read efficiency
    if not network_config_cache:
        with open(network_config, 'r') as f:
            network_config_dict = json.load(f)
        network_config_cache = network_config_dict

    return network_config_cache[param]


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
    if info[-4] == 'compute':
        region = info[-5]
    elif info[-4] == 'compute-1':
        region = 'us-east-1'
    else:
        raise ValueError("cannot deduce region from name {}".format(info))
    return region


def verify_nodes_same_region(region, array_ip):
    for ip in array_ip:
        if retrieve_instance_region(ip) != region:
            sys.exit(
                "All nodes registered for the same endpoints should be located in the region, if not, gracefully exit!! ")


def create_name_target_group(shard, id_domain):
    ret = []
    tg_prefix = 'tg-s' + str(shard) + '-api-' + id_domain + '-'
    ret.append(tg_prefix + 'https')
    ret.append(tg_prefix + 'wss')
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


def create_name_record_set(shard, id_domain):
    ret = [
        'api.s' + str(shard) + '.' + id_domain,
        'ws.s' + str(shard) + '.' + id_domain
    ]
    return ret
