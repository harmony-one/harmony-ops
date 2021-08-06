import os
import json
import copy
import subprocess
from dotenv import load_dotenv, find_dotenv
import yaml
import logging
import argparse
import requests

# grafana api host
grafana_api_host = "https://monitor.harmony.one/api/"
# set shard count
shard_count = 4
# min storage space for alerting
min_storage_space = 5
# max actual usage memory rate for alerting
max_actual_usage_memory_rate = 80
# scrape_interval for every shard in prometheus
prometheus_scrape_interval = 5
# this grafana folder id dict for mode
dict_grafana_folder_mode = {
    "mainnet": 18,
    "ostn": 19,
    "stn": 20,
    "test": 31,
    "lrtn": 45,
    "pstn": 46,
    "dryrun": 52,
    "testnet": 105
}
do_node_ips = ["143.110.234.143", "138.68.11.38", "143.110.234.143"]
local_disk_node_ips = ["3.236.64.29", "18.116.33.241", "52.53.250.187", "35.82.29.182", "34.229.131.248", "54.189.61.183", "54.188.66.208", "34.216.159.65", "54.212.179.219", "44.235.31.107", "44.241.141.240", "44.237.240.249", "44.225.100.239", "34.222.190.168", "44.230.211.156"]


def shcmd(cmd, ignore_error=False):
    ret = subprocess.call(cmd, shell=True)
    if ignore_error is False and ret != 0:
        raise RuntimeError("Failed to execute {}. Return code:{}".format(
            cmd, ret))
    return ret


# get latest node ips from github
def download_ip_list_from_github(git_token, mode):
    if mode == "lrtn":
        github_dir = "testnet"
    else:
        github_dir = mode

    # download list of IP from shard
    for index in range(shard_count):
        url_path = "https://raw.githubusercontent.com/harmony-one/nodedb/" \
                   "master/{github_dir}/shard{shard_index}.txt".format(shard_index=index, github_dir=github_dir)
        cmd = "curl -H 'Authorization: token {token}' " \
              "-H 'Accept: application/vnd.github.v3.raw' -o ips/{mode}/shard{shard_index}.txt " \
              "{path}".format(token=git_token, shard_index=index, path=url_path, mode=mode)
        shcmd(cmd)

    if mode == "mainnet":
        # download list of DNS IP from shard
        for index in range(shard_count):
            url_path = "https://raw.githubusercontent.com/harmony-one/nodedb/" \
                       "master/{github_dir}/dns.shard{shard_index}.txt".format(shard_index=index, github_dir=github_dir)
            cmd = "curl -H 'Authorization: token {token}' " \
                  "-H 'Accept: application/vnd.github.v3.raw' -o ips/{mode}/dns.shard{shard_index}.txt " \
                  "{path}".format(token=git_token, shard_index=index, path=url_path, mode=mode)
            shcmd(cmd)

        # download list of EXP IP from shard
        for index in range(shard_count):
            url_path = "https://raw.githubusercontent.com/harmony-one/nodedb/" \
                       "master/{github_dir}/shard{shard_index}exp.txt".format(shard_index=index, github_dir=github_dir)
            cmd = "curl -H 'Authorization: token {token}' " \
                  "-H 'Accept: application/vnd.github.v3.raw' -o ips/{mode}/shard{shard_index}exp.txt " \
                  "{path}".format(token=git_token, shard_index=index, path=url_path, mode=mode)
            shcmd(cmd)


def load_file_to_json(json_file):
    with open(json_file) as f_db_shard:
        return json.load(f_db_shard)


def load_file_to_yaml(yaml_file):
    with open(yaml_file) as f_db_shard:
        return yaml.load(f_db_shard, Loader=yaml.FullLoader)


def load_file_to_array(txt_file):
    ip_array = []
    with open(txt_file) as f_file:
        for line in f_file:
            ip_array.append(line.rstrip())
    return ip_array


def load_file_split_to_array(txt_file):
    ip_array = []
    with open(txt_file) as f_file:
        for line in f_file:
            ip_array.extend(line.rstrip().split(" "))
    return ip_array


# create grafana whole config file
def create_grafana_config(mode, category, dict_ip_array, dict_dns_ip_array, dict_exp_ip_array,
                          shard_dashboard_template_json, dict_part_temp_json):
    dict_shard_dashboard_json = {}
    for ind in range(shard_count):
        ip_array = {"dns": [], "node": []}
        ip_created = []

        if mode == "mainnet":
            # load dns and exp ip list
            ip_array["dns"] = dict_dns_ip_array.get(ind)

            all_ip_array = dict_ip_array.get(ind)
            for ip in all_ip_array:
                if ip in ip_array["dns"]:
                    continue
                else:
                    ip_array["node"].append(ip)
        else:
            ip_array["node"] = dict_ip_array.get(ind)

        # special job name
        if mode == "test":
            job_name = "shard0_mainnet"
        else:
            job_name = "shard{shard_index}_{mode}".format(shard_index=ind, mode=mode)

        shard_dashboard_json = copy.deepcopy(shard_dashboard_template_json)
        # modify dashboard uid
        shard_dashboard_json["uid"] = "{mode}_shard{shard_index}_{category}".format(mode=mode, shard_index=ind,
                                                                                    category=category)
        # modify dashboard title
        shard_dashboard_json["title"] = "{mode} - {category} - SHARD {shard_index}".format(
            mode=mode.upper(), category=category.upper(), shard_index=ind)
        # modify global stat
        shard_dashboard_json["panels"][2]["targets"][0].update(
            {"expr": "count(up{{job=\"{shard}\"}}==1)".format(shard=job_name)})
        shard_dashboard_json["panels"][3]["targets"][0].update(
            {"expr": "up{{job=\"{shard}\"}}==0".format(shard=job_name)})
        shard_dashboard_json["panels"][3]["targets"][1].update(
            {"expr": "count(up{{job=\"{shard}\"}}==0)".format(shard=job_name)})

        id_0 = 10
        y_point = 10

        for node_type in ip_array:
            ips = ip_array[node_type]
            # skip the empty node set
            if not len(ips):
                continue

            # add row panel
            id_0 += 2
            row_panel = {
                "collapsed": True,
                "datasource": "null",
                "gridPos": {"h": 1, "w": 24, "x": 0, "y": y_point},
                "id": id_0,
                "panels": [],
                "title": node_type.upper(),
                "type": "row"
            }
            y_point += 1

            ips_size = len(ips)
            for idx in range(ips_size):
                ip = ips[idx].rstrip()

                if ip == "" or ip in ip_created:
                    continue

                if category == "base":
                    for part_index in range(4):
                        id_0 += 2

                        x_point = part_index * 6

                        # create panel for base metric
                        data_part_json = create_grafana_base_panel_config(mode, ind, ip, part_index, job_name,
                                                                          dict_part_temp_json)

                        data_part_json.update({"gridPos": {'h': 6, 'w': 6, 'x': x_point, 'y': y_point},
                                               "id": id_0
                                               })
                        # insert this chart to dashboard.panels
                        row_panel["panels"].append(data_part_json)
                elif category == "network":
                    for part_index in range(2):
                        id_0 += 2

                        x_point = part_index * 12

                        # create panel for network metric
                        data_part_json = create_grafana_network_panel_config(mode, ind, ip, part_index, job_name,
                                                                             dict_part_temp_json)

                        data_part_json.update({"gridPos": {'h': 6, 'w': 12, 'x': x_point, 'y': y_point},
                                               "id": id_0
                                               })

                        # insert this chart to dashboard.panels
                        row_panel["panels"].append(data_part_json)

                y_point += 6

                # record created ip to avoid create duplicate
                ip_created.append(ip)

            if node_type == "dns":
                # auto collapse row for dns
                row_panel_child = row_panel["panels"]
                row_panel["panels"] = []
                row_panel["collapsed"] = False
                shard_dashboard_json["panels"].append(row_panel)
                shard_dashboard_json["panels"].extend(row_panel_child)
            else:
                shard_dashboard_json["panels"].append(row_panel)

        dict_shard_dashboard_json[ind] = shard_dashboard_json
    return dict_shard_dashboard_json


# create grafana base metric config file
def create_grafana_base_panel_config(mode, ind, ip, part_index, job_name, dict_part_temp_json):
    data_part_json = {}
    title_chart = ""

    # FIRST COLUMN - CPU Monitoring
    if part_index == 0:
        # load cpu metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["cpu"])

        # add an alert for CPU
        data_part_json["alert"][
            "message"] = "the cpu usage rate of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode,
                                                                                                             shard_index=ind,
                                                                                                             ip=ip)
        # no need alert network
        if mode not in ["mainnet"]:
            data_part_json["alert"]["notifications"] = []

        cpu_query = "100 - (avg by (instance) (irate(node_cpu_seconds_total{{instance=\"{ip}:9100\", job=\"{job_name}\",mode=\"idle\"}}[5m])) * 100)".format(
            ip=ip, job_name=job_name)

        title_chart = "CPU UTILIZATION - "
        data_part_json["targets"][0].update({"expr": cpu_query})
    # SECOND COLUMN - RAM Monitoring
    elif part_index == 1:
        # load ram metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["ram"])

        # add an alert for Memory
        data_part_json["alert"][
            "message"] = "the memory usage rate of the {mode} shard{shard_index} node({ip}) is abnormal".format(
            mode=mode, shard_index=ind, ip=ip)
        # no need alert network
        if mode not in ["mainnet"]:
            data_part_json["alert"]["notifications"] = []

        ram_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}} - node_memory_" \
                    "MemFree_bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}}) / node_memory_MemTotal_" \
                    "bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}} * 100".format(ip=ip, job_name=job_name)

        ram_actual_usage_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}} - node_memory_" \
                                 "MemAvailable_bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}}) * 100 / node_memory_" \
                                 "MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{job_name}\"}}".format(ip=ip,
                                                                                                      job_name=job_name)

        title_chart = "MEMORY - "
        data_part_json["targets"][0].update({"expr": ram_query})
        data_part_json["targets"][1].update({"expr": ram_actual_usage_query})
    # THIRD COLUMN - DISK Monitoring
    elif part_index == 2:
        # load disk metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["disk"])

        # add an alert for storage
        data_part_json["alert"][
            "message"] = "the free space of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode,
                                                                                                         shard_index=ind,
                                                                                                         ip=ip)
        # no need alert network
        if mode not in ["mainnet"]:
            data_part_json["alert"]["notifications"] = []

        # disk_query = "node_filesystem_avail_bytes{{instance=\"{ip}:9100\", job=\"{job_name}\", mountpoint=\"/\"}}/1024/1024/1024"
        if ip in do_node_ips:
            disk_query = "(1-(node_filesystem_free_bytes{{instance=\"{ip}:9100\", job=\"{job_name}\", " \
                         "device=\"/dev/sda\", fstype=~\"ext4|xfs\"}} / node_filesystem_size_bytes{{instance=\"{ip}:9100\", " \
                         "job=\"{job_name}\", device=\"/dev/sda\", fstype=~\"ext4|xfs\"}} )) * 100".format(ip=ip, job_name=job_name)
        else:
            if ip in local_disk_node_ips:
                mountpoint = "/data"
            else:
                mountpoint = "/"
                
            disk_query = "(1-(node_filesystem_free_bytes{{instance=\"{ip}:9100\", job=\"{job_name}\", " \
                     "mountpoint=\"{mountpoint}\", fstype=~\"ext4|xfs\"}} / node_filesystem_size_bytes{{instance=\"{ip}:9100\", " \
                     "job=\"{job_name}\", mountpoint=\"{mountpoint}\", fstype=~\"ext4|xfs\"}} )) * 100".format(ip=ip, job_name=job_name, mountpoint=mountpoint)

        title_chart = "DISK SPACE -"

        data_part_json["targets"][0].update({"expr": disk_query})
    # FOURTH COLUMN - DISK IO Monitoring
    elif part_index == 3:
        # load io metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["io"])

        io_read_query = "irate(node_disk_reads_completed_total{{instance=\"{ip}:9100\", job=\"{job_name}\"}}[5m])".format(
            ip=ip, job_name=job_name)
        io_write_query = "irate(node_disk_writes_completed_total{{instance=\"{ip}:9100\", job=\"{job_name}\"}}[5m])".format(
            ip=ip, job_name=job_name)

        title_chart = "DISK IO - "

        data_part_json["targets"][0].update({"expr": io_read_query})
        data_part_json["targets"][1].update({"expr": io_write_query})
    else:
        pass

    # set panel title
    data_part_json["title"] = title_chart + ip

    return data_part_json


# create grafana network metric config file
def create_grafana_network_panel_config(mode, ind, ip, part_index, shard, dict_part_temp_json):
    data_part_json = {}
    title_chart = ""

    # FIRST COLUMN - NETWORK Monitoring
    if part_index == 0:
        # load net metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["net"])

        # add an alert for network traffic
        data_part_json["alert"][
            "message"] = "the network traffic of the {mode} shard{shard_index} node({ip}) is abnormal".format(
            mode=mode, shard_index=ind, ip=ip)
        # no need alert network
        if mode not in ["mainnet"]:
            data_part_json["alert"]["notifications"] = []

        network_incoming_query = "rate(node_network_receive_bytes_total{{instance" \
                                 "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
            ip=ip, shard=shard)
        network_outgoing_query = "rate(node_network_transmit_bytes_total{{instance" \
                                 "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
            ip=ip, shard=shard)

        title_chart = "NETWORK TRAFFIC - "

        data_part_json["targets"][0].update({"expr": network_incoming_query})
        data_part_json["targets"][1].update({"expr": network_outgoing_query})
    # SECOND COLUMN - RAM Monitoring
    elif part_index == 1:
        # load tcp metric template
        data_part_json = copy.deepcopy(dict_part_temp_json["tcp"])

        tcp_alloc = "node_sockstat_TCP_alloc{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip,
                                                                                               shard=shard)
        tcp_inuse = "node_sockstat_TCP_inuse{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip,
                                                                                               shard=shard)
        tcp_mem = "node_sockstat_TCP_mem{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip,
                                                                                           shard=shard)

        title_chart = "TCP SOCK - "
        data_part_json["targets"][0].update({"expr": tcp_alloc})
        data_part_json["targets"][1].update({"expr": tcp_inuse})
        data_part_json["targets"][2].update({"expr": tcp_mem})
    else:
        pass

    # set panel title
    data_part_json["title"] = title_chart + ip

    return data_part_json


# create prometheus whole config file
def create_prometheus_config(mode, dict_ip_array, config_template):
    total_config_part_count = len(config_template["scrape_configs"])

    for ind in range(shard_count):
        # find config part index
        job_name = "shard{shard_index}_{mode}".format(shard_index=ind, mode=mode)
        for part_index in range(total_config_part_count):
            if job_name == config_template["scrape_configs"][part_index]["job_name"]:
                ip_array = dict_ip_array.get(ind)
                ip_array_size = len(ip_array)

                targets = []

                for idx in range(ip_array_size):
                    ip = ip_array[idx].rstrip()

                    if ip == "":
                        continue

                    targets.append(ip + ":9100")

                config_template["scrape_configs"][part_index]["scrape_interval"] = str(prometheus_scrape_interval) + "s"
                config_template["scrape_configs"][part_index]["static_configs"][0]["targets"] = targets
                break

    with open("prometheus/prometheus.yml", 'w') as fp:
        yaml.dump(config_template, fp)


# update prometheus config
def update_prometheus_config():
    cmd = "sudo cp prometheus/prometheus.yml /etc/prometheus/prometheus.yml && sudo systemctl restart prometheus"
    shcmd(cmd)


# update grafana config
def update_grafana_config(mode, category, dict_shard_dashboard_json, grafana_token):
    for index in range(shard_count):
        # get now dashboard version
        url = grafana_api_host + "dashboards/uid/{mode}_shard{shard_index}_{category}".format(mode=mode,
                                                                                              shard_index=index,
                                                                                              category=category)
        headers = {"Authorization": "Bearer " + grafana_token}
        response = requests.get(url, headers=headers).json()

        # check new dashboard
        if "dashboard" in response:
            version = response["dashboard"]["version"]
        else:
            version = 1

        # post new dashboard config
        dict_shard_dashboard_json[index]["version"] = version
        new_dashboard_config = {
            "dashboard": dict_shard_dashboard_json[index],
            "folderId": dict_grafana_folder_mode[mode],
            "overwrite": False
        }
        url = grafana_api_host + "dashboards/db"
        headers = {"Authorization": "Bearer " + grafana_token, "Content-Type": "application/json"}
        response = requests.post(url, data=json.dumps(new_dashboard_config), headers=headers).json()

        if response["status"] == "success":
            logging.info("update grafana dashboard config success for " + response["uid"])
        else:
            logging.error("failed to update grafana dashboard config: " + json.dumps(response))


def main():
    global min_storage_space, prometheus_scrape_interval, shard_count, grafana_api_host, max_actual_usage_memory_rate
    logging.basicConfig(level=10, format='%(asctime)s %(filename)s[line:%(lineno)d] %(levelname)s %(message)s')

    # get config by .env file
    load_dotenv(find_dotenv())

    min_storage_space = os.getenv("MIN_STORAGE_SPACE")
    max_actual_usage_memory_rate = os.getenv("MAX_ACTUAL_USAGE_MEMORY_RATE")
    prometheus_scrape_interval = os.getenv("PROMETHEUS_SCRAPE_INTERVAL")

    # get private github token
    git_token = os.getenv("GIT_TOKEN")

    # get grafana api token
    grafana_token = os.getenv("GRAFANA_TOKEN")
    grafana_api_host = os.getenv("GRAFANA_API_HOST")

    if git_token == "" or grafana_token == "":
        raise RuntimeError("need to set token")

    # load grafana metric template files
    dict_part_temp_json = {
        "cpu": load_file_to_json("grafana_template/cpu_template.json"),
        "ram": load_file_to_json("grafana_template/ram_template.json"),
        "disk": load_file_to_json("grafana_template/disk_space_template.json"),
        "io": load_file_to_json("grafana_template/disk_io_count_template.json"),
        "net": load_file_to_json("grafana_template/net_traffic_template.json"),
        "tcp": load_file_to_json("grafana_template/net_sock_tcp_template.json"),
    }

    # get script run mode
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', type=str, help="select run mode. mainnet ostn stn etc.")
    args = parser.parse_args()
    if args.m not in ["all", "mainnet", "testnet", "test"]:
        raise RuntimeError("need to set correct network mode")
    elif args.m == "all":
        run_modes = ["mainnet", "testnet"]
    else:
        run_modes = [args.m]

    # update for each mode network
    for mode in run_modes:
        # special shard count for stn & test
        if mode in ["test"]:
            shard_count = 1
        else:
            shard_count = 4

        # get latest node ips from github
        download_ip_list_from_github(git_token, mode)

        logging.info('download ip list success')

        dict_ip_array = {}
        dict_dns_ip_array = {}
        dict_exp_ip_array = {}

        # load grafana dashboard template files
        file_path = "grafana_template/dashboard_template.json"
        shard_dashboard_template_json = load_file_to_json(file_path)

        # load latest node ip files
        for index in range(shard_count):
            file_path = "ips/{mode}/shard{shard_index}.txt".format(shard_index=index, mode=mode)
            dict_ip_array[index] = load_file_to_array(file_path)

        if mode == "mainnet":
            # load latest dns node ip files
            for index in range(shard_count):
                file_path = "ips/{mode}/dns.shard{shard_index}.txt".format(shard_index=index, mode=mode)
                dict_dns_ip_array[index] = load_file_split_to_array(file_path)

            # load latest exp node ip files
            for index in range(shard_count):
                file_path = "ips/{mode}/shard{shard_index}exp.txt".format(shard_index=index, mode=mode)
                dict_exp_ip_array[index] = load_file_to_array(file_path)

        # load prometheus config template
        if os.path.exists("prometheus/prometheus.yml"):
            prometheus_config_template = load_file_to_yaml("prometheus/prometheus.yml")
        else:
            prometheus_config_template = load_file_to_yaml("prometheus_template/prometheus.yml")

        # create prometheus whole config file
        create_prometheus_config(mode, dict_ip_array, prometheus_config_template)
        logging.info('create prometheus config success')

        for category in ["base", "network"]:
            # create grafana whole config file
            dict_shard_dashboard_json = create_grafana_config(mode, category, dict_ip_array, dict_dns_ip_array,
                                                              dict_exp_ip_array,
                                                              shard_dashboard_template_json, dict_part_temp_json)
            logging.info('create grafana config success')

            # update grafana config
            update_grafana_config(mode, category, dict_shard_dashboard_json, grafana_token)
            logging.info('update grafana config success')

    # update prometheus config and restart service
    update_prometheus_config()
    logging.info('update prometheus config success')


if __name__ == "__main__":
    main()
