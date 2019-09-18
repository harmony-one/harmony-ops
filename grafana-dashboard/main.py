"""
PURPOSE: a python script to programmatically generate a Grafana dashboard to monitor performances of harmony nodes

    Author: Andy Bo Wu
    Date:   July 8, 2019


DEPENDENCY:
    * requests v2.22.0: https://2.python-requests.org/en/master/#
    *



REFERENCE
    * https://grafana.com/docs/http_api/dashboard/
    * https://grafana.com/docs/reference/http_api/


"""
import os
import botocore
import requests
import boto3
import json
import copy
from pprint import pprint
from CREDENTIAL import SECRET_API_KEY

bucket_host = r"harmony-benchmark"
files_array = ['logs/2019/06/28/153354/validator/shard0.txt', 'logs/2019/06/28/153354/validator/shard1.txt', 'logs/2019/06/28/153354/validator/shard2.txt', 'logs/2019/06/28/153354/validator/shard3.txt']

# TO-DO
leader_array = ['', '', '', '']

def download_host():

    s3 = boto3.resource('s3')

    for file in files_array:
        try:
            s3.Bucket(bucket_host).download_file(file, os.path.basename(file))
        except botocore.exceptions.ClientError as e:
            if e.response['Error']['Code'] == "404":
                print("The object does not exist.")
            else:
                raise

# TO-DO
def add_leader_ip():
    pass


def add_cpu_ram_disk_charts():

    # load dashboard_shard0.json
    with open('dashboard_shard0.json') as f_db_shard0:
        data_db_shard0 = json.load(f_db_shard0)

    # load dashboard_shard1.json
    with open('dashboard_shard1.json') as f_db_shard1:
        data_db_shard1 = json.load(f_db_shard1)

    # load dashboard_shard2.json
    with open('dashboard_shard2.json') as f_db_shard2:
        data_db_shard2 = json.load(f_db_shard2)

    # load dashboard_shard3.json
    with open('dashboard_shard3.json') as f_db_shard3:
        data_db_shard3 = json.load(f_db_shard3)



    # load cpu template
    with open('cpu_template.json') as f_cpu_template:
        data_cpu_temp = json.load(f_cpu_template)

    # read shard.txt, and load ip address into an array
    with open('shard0.txt') as f_shard0:
        ip_array_shard0 = []
        for line in f_shard0:
            ip_array_shard0.append(line)

    with open('shard1.txt') as f_shard1:
        ip_array_shard1 = []
        for line in f_shard1:
            ip_array_shard1.append(line)

    with open('shard2.txt') as f_shard2:
        ip_array_shard2 = []
        for line in f_shard2:
            ip_array_shard2.append(line)

    with open('shard3.txt') as f_shard3:
        ip_array_shard3 = []
        for line in f_shard3:
            ip_array_shard3.append(line)




    dict_ip_array = {
        0 : ip_array_shard0,
        1 : ip_array_shard1,
        2 : ip_array_shard2,
        3 : ip_array_shard3
    }

    dict_shard = {
        0 : "shard0",
        1 : "shard1",
        2 : "shard2",
        3 : "shard3"
    }

    dict_data_db_shard = {
        0 : data_db_shard0,
        1 : data_db_shard1,
        2 : data_db_shard2,
        3 : data_db_shard3
    }

    dict_db_shard = {
        0 : "db_shard0.json",
        1 : "db_shard1.json",
        2 : "db_shard2.json",
        3 : "db_shard3.json"
    }

    for ind in range(4):

        ip_array = dict_ip_array.get(ind)
        ip_array_size = len(ip_array)

        shard = dict_shard.get(ind)

        data_db_shard = dict_data_db_shard.get(ind)

        id_0 = 4

        db_shard = dict_db_shard.get(ind)

        for idx in range(ip_array_size):
            ip = ip_array[idx]
            for idy in range(3):
                id_0 += 2

                x_point = idy * 8
                y_point = (idx+1) * 8

                cpu_query = "100 - (avg by (instance) (irate(node_cpu_seconds_total{instance=\""+ip.rstrip()+':9100\",job=\"'+shard+'\",mode=\"idle\"}[5m])) * 100)'
                ram_query = "(node_memory_MemTotal_bytes{instance=\""+ip.rstrip()+':9100\",job=\"'+shard+'\"} - node_memory_MemFree_bytes{instance=\"'+ip.rstrip()+':9100\",job=\"'+shard+'\"}) / node_memory_MemTotal_bytes{instance=\"'+ip.rstrip()+':9100\",job=\"'+shard+'\"} * 100'
                disk_query = "node_filesystem_avail_bytes{instance=\""+ip.rstrip()+':9100\",job=\"'+shard+'\", mountpoint="/"}/1024/1024/1024'


                ## start to customize the chart
                data_cpu_insert = copy.deepcopy(data_cpu_temp)

                # customize title and targets.expr
                # FIRST COLUMN - CPU Monitoring
                if (x_point == 0):
                    title_chart = "CPU - "
                    data_cpu_insert["targets"][0].update({"expr" : cpu_query})
                # SECOND COLUMN - RAM Monitoring
                elif (x_point == 8):
                    title_chart = "RAM - "
                    data_cpu_insert["targets"][0].update({"expr" : ram_query})
                # THIRD COLUMN - DISK Monitoring
                elif (x_point == 16):
                    title_chart = "DISK -"
                    data_cpu_insert["targets"][0].update({"expr" : disk_query})
                else:
                    pass


                data_cpu_insert.update({"gridPos" : {'h' : 8, 'w' : 8, 'x' : x_point, 'y' : y_point},
                                      "id" : id_0,
                                      "title": title_chart + ip
                                      })

                # insert this chart to dashboard.panels
                data_db_shard["dashboard"]["panels"].append(data_cpu_insert)



        with open(db_shard, 'w') as fp:
            json.dump(data_db_shard, fp)


def main():

    download_host()

    add_cpu_ram_disk_charts()


    # Attn: NEED TO MOVE THIS INTO A FILE, AND PUT IT INTO .GITIGNORE
    API_KEY = SECRET_API_KEY


    # POST/CREATE a dashboard
    URL_update_db = 'http://api_key:' + API_KEY + '@grafana.harmony.one:3000/api/dashboards/db'


    headers = {"Content-Type": 'application/json'}

    # CREATE a dashboard
    # TO-DO: loop + exception handling
    # response0 = requests.post(URL_update_db, data=open('create_db_0.json', 'rb'), headers=headers)
    # response1 = requests.post(URL_update_db, data=open('create_db_1.json', 'rb'), headers=headers)
    # response2 = requests.post(URL_update_db, data=open('create_db_2.json', 'rb'), headers=headers)
    # response3 = requests.post(URL_update_db, data=open('create_db_3.json', 'rb'), headers=headers)

    # DELETE a dashboard
    # uid_db = 'laloA8MZz'
    # URL_delete_db = 'http://api_key:' + API_KEY + '@grafana.harmony.one:3000/api/dashboards/uid/' + uid_db
    # response = requests.delete(URL_delete_db, headers=headers)


    # UPDATE a dashboard
    response0 = requests.post(URL_update_db, data=open('db_shard0.json', 'rb'), headers=headers)
    response1 = requests.post(URL_update_db, data=open('db_shard1.json', 'rb'), headers=headers)
    response2 = requests.post(URL_update_db, data=open('db_shard2.json', 'rb'), headers=headers)
    response3 = requests.post(URL_update_db, data=open('db_shard3.json', 'rb'), headers=headers)


    print("STATUS CODES")
    pprint(response0.status_code)
    pprint(response1.status_code)
    pprint(response2.status_code)
    pprint(response3.status_code)
    # pprint(response0.text)


if __name__ == '__main__':
    main()
