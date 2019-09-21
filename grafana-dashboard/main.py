import os
import sys
import boto3
import botocore
import requests
import json
import pprint
import copy
from dotenv import load_dotenv

load_dotenv()

bucket_log = r'harmony-benchmark'

log_path = r'logs/2019/06/28/153354/'

path_dist_config_legacy = log_path + r'distribution_config.txt'
path_shard0_tf = log_path + r'shard0.txt'
path_shard1_tf = log_path + r'shard1.txt'
path_shard2_tf = log_path + r'shard2.txt'
path_shard3_tf = log_path + r'shard3.txt'

f_array = [path_shard0_tf,
           path_shard1_tf,
           path_shard2_tf,
           path_shard3_tf]


API_SECRET = os.getenv("SECRET_KEY")
Grafana_IP = os.getenv("GRAFANA_IP")

headers = {"Content-Type": 'application/json'}
URL_update_db = 'http://api_key:' + API_SECRET + \
    '@' + Grafana_IP + ':3000/api/dashboards/db'

shard0_ip_array = []
shard1_ip_array = []
shard2_ip_array = []
shard3_ip_array = []

dict_shard = {
    0: "shard0",
    1: "shard1",
    2: "shard2",
    3: "shard3"
}

dict_db_shard = {
    0: "db_shard0.json",
    1: "db_shard1.json",
    2: "db_shard2.json",
    3: "db_shard3.json"
}

# min_storage_space for alerting
min_storage_space = 5

def download_ip_list_from_s3(files_array):

    s3 = boto3.resource('s3')

    for file in files_array:
        try:
            s3.Bucket(bucket_log).download_file(file, os.path.basename(file))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise


def load_file_to_json(json_file):
    with open(json_file) as f_db_shard0:
        return json.load(f_db_shard0)


def load_file_to_array(txt_file):
    ip_array = []
    with open(txt_file) as f_file:
        for line in f_file:
            ip_array.append(line)
    return ip_array


def add_cpu_ram_disk_charts(dict_ip_array, dict_shard, dict_shard_json_db_offline, cpu_temp_json):

    for ind in range(4):
        ip_array = dict_ip_array.get(ind)
        ip_array_size = len(ip_array)
        # ip_array_size = 2

        shard = dict_shard.get(ind)

        data_db_shard = dict_shard_json_db_offline.get(ind)

        id_0 = 4

        db_shard = dict_db_shard.get(ind)

        for idx in range(ip_array_size):
            ip = ip_array[idx].rstrip()
            for idy in range(4):
                id_0 += 2

                x_point = idy * 6
                y_point = (idx+1) * 6

                cpu_query = "100 - (avg by (instance) (irate(node_cpu_seconds_total{instance=\"" + \
                    ip+':9100\",job=\"'+shard+'\",mode=\"idle\"}[5m])) * 100)'
                ram_query = "(node_memory_MemTotal_bytes{instance=\""+ip+':9100\",job=\"'+shard+'\"} - node_memory_MemFree_bytes{instance=\"'+ip.rstrip(
                )+':9100\",job=\"'+shard+'\"}) / node_memory_MemTotal_bytes{instance=\"'+ip.rstrip()+':9100\",job=\"'+shard+'\"} * 100'
                memory_actual_usage_query = "(node_memory_MemTotal_bytes{instance=\""+ip+":9100\"} - node_memory_MemAvailable_bytes{instance=\"" + \
                    ip+":9100\"}) * 100/ node_memory_MemTotal_bytes{instance=\""+ip+":9100\"}"
                disk_query = "node_filesystem_avail_bytes{instance=\""+ip + \
                    ':9100\",job=\"'+shard+'\", mountpoint="/"}/1024/1024/1024'
                network_incoming_query = "rate(node_network_receive_bytes_total{instance=\"" + \
                    ip+":9100\", device=\"eth0\"}[5m]) / 1024"
                network_outgoing_query = "rate(node_network_transmit_bytes_total{instance=\"" + \
                    ip+":9100\", device=\"eth0\"}[5m]) / 1024"

                # start to customize the chart
                data_cpu_insert = copy.deepcopy(cpu_temp_json)

                temp_expr_2 = {
                    "expr": "",
                    "format": "time_series",
                    "intervalFactor": 1,
                    "legendFormat": "",
                    "refId": ""
                }

                # customize title and targets.expr
                # FIRST COLUMN - CPU Monitoring
                if (x_point == 0):
                    title_chart = "CPU UTILIZATION - "
                    data_cpu_insert["targets"][0].update({"expr": cpu_query})
                    data_cpu_insert["yaxes"][0].update({"label": "%"})
                # SECOND COLUMN - RAM Monitoring
                elif (x_point == 6):
                    title_chart = "MEMORY - "
                    data_cpu_insert["targets"][0].update({"expr": ram_query})
                    data_cpu_insert["targets"][0].update(
                        {"legendFormat": "Occupied Memory"})
                    data_cpu_insert["yaxes"][0].update({"label": "%"})
                    data_cpu_insert["targets"].append(temp_expr_2.copy())
                    data_cpu_insert["targets"][1].update({
                        "expr": memory_actual_usage_query,
                        "legendFormat": "Actual Usage",
                        "refId": "B"
                    })

                # THIRD COLUMN - DISK Monitoring
                elif (x_point == 12):
                    # add an alert for low storage
                    alert_json = {
                        "alertRuleTags": {},
                        "conditions": [
                            {
                                "evaluator": {
                                    "params": [
                                        min_storage_space
                                    ],
                                    "type": "lt"
                                },
                                "operator": {
                                    "type": "and"
                                },
                                "query": {
                                    "params": [
                                        "A",
                                        "5m",
                                        "now"
                                    ]
                                },
                                "reducer": {
                                    "params": [],
                                    "type": "avg"
                                },
                                "type": "query"
                            }
                        ],
                        "for": "5m",
                        "frequency": "1m",
                        "handler": 1,
                        "message": "Run out of storage space",
                        "name": "Node is running out of storage space",
                        "noDataState": "no_data",
                        "notifications": [
                            {
                                "uid": "2yKOXNpWk"
                            }
                        ]
                    }

                    title_chart = "FREE SPACE -"
                    data_cpu_insert["targets"][0].update({"expr": disk_query})
                    data_cpu_insert["yaxes"][0].update({"label": "GB"})
                    # data_cpu_insert.update({"alert" : alert_json})


                elif (x_point == 18):
                    title_chart = "NETWORK TRAFFIC - "
                    temp_expr = {
                        "expr": network_incoming_query,
                        "format": "time_series",
                        "intervalFactor": 1,
                        "legendFormat": "INCOMING",
                        "refId": "A"
                    }
                    data_cpu_insert["targets"].append(temp_expr.copy())
                    data_cpu_insert["targets"].append(temp_expr.copy())
                    # update outgoing traffic
                    data_cpu_insert["targets"][1].update({
                        "expr": network_outgoing_query,
                        "legendFormat": "OUTGOING",
                        "refId": "B"
                    })
                    data_cpu_insert["yaxes"][0].update({"label": "KB"})
                else:
                    pass

                data_cpu_insert.update({"gridPos": {'h': 6, 'w': 6, 'x': x_point, 'y': y_point},
                                        "id": id_0,
                                        "title": title_chart + ip
                                        })

                # insert this chart to dashboard.panels
                data_db_shard["dashboard"]["panels"].append(data_cpu_insert)

        with open(db_shard, 'w') as fp:
            json.dump(data_db_shard, fp)


def main():

    download_ip_list_from_s3(f_array)

    shard0_json_db_offline = load_file_to_json("shard0_db_offline.json")
    shard1_json_db_offline = load_file_to_json("shard1_db_offline.json")
    shard2_json_db_offline = load_file_to_json("shard2_db_offline.json")
    shard3_json_db_offline = load_file_to_json("shard3_db_offline.json")

    cpu_temp_json = load_file_to_json("cpu_template.json")

    shard0_ip_array = load_file_to_array("shard0.txt")
    shard1_ip_array = load_file_to_array("shard1.txt")
    shard2_ip_array = load_file_to_array("shard2.txt")
    shard3_ip_array = load_file_to_array("shard3.txt")

    dict_ip_array = {
        0: shard0_ip_array,
        1: shard1_ip_array,
        2: shard2_ip_array,
        3: shard3_ip_array
    }

    dict_shard_json_db_offline = {
        0: shard0_json_db_offline,
        1: shard1_json_db_offline,
        2: shard2_json_db_offline,
        3: shard3_json_db_offline
    }

    add_cpu_ram_disk_charts(dict_ip_array, dict_shard,
                            dict_shard_json_db_offline, cpu_temp_json)

    try:
        resp0 = requests.post(URL_update_db, data=open(
            'db_shard0.json', 'rb'), headers=headers)
        resp0.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("RESP - 0")
        print(e)
        sys.exit(1)

    try:
        resp1 = requests.post(URL_update_db, data=open(
            'db_shard1.json', 'rb'), headers=headers)
        resp1.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("RESP - 1")
        print(e)
        sys.exit(1)

    try:
        resp2 = requests.post(URL_update_db, data=open(
            'db_shard2.json', 'rb'), headers=headers)
        resp2.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("RESP - 2")
        print(e)
        sys.exit(1)

    try:
        resp3 = requests.post(URL_update_db, data=open(
            'db_shard3.json', 'rb'), headers=headers)
        resp3.raise_for_status()
    except requests.exceptions.RequestException as e:
        print("RESP - 3")
        print(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
