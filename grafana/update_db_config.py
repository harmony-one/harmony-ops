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
    "dryrun": 52
}


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

    # download list of IP from shard, and save it to file
    for index in range(shard_count):
        url_path = "https://raw.githubusercontent.com/harmony-one/nodedb/" \
                   "master/{github_dir}/shard{shard_index}.txt".format(shard_index=index, github_dir=github_dir)
        cmd = "curl -H 'Authorization: token {token}' " \
              "-H 'Accept: application/vnd.github.v3.raw' -o ips/{mode}/shard{shard_index}.txt " \
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
            ip_array.append(line)
    return ip_array


# create grafana whole config file
def create_grafana_config(mode, category, dict_ip_array, shard_dashboard_template_json, dict_part_temp_json):
    dict_shard_dashboard_json = {}
    for ind in range(shard_count):
        ip_array = dict_ip_array.get(ind)
        ip_array_size = len(ip_array)

        if mode == "test":
            shard = "shard0_mainnet"
        else:
            shard = "shard{shard_index}_{mode}".format(shard_index=ind, mode=mode)

        shard_dashboard_json = copy.deepcopy(shard_dashboard_template_json)
        # modify dashboard uid
        shard_dashboard_json["uid"] = "{mode}_shard{shard_index}_{category}".format(mode=mode, shard_index=ind, category=category)
        # modify dashboard title
        shard_dashboard_json["title"] = "{mode} - {category} - SHARD {shard_index}".format(
            mode=mode.upper(), category=category.upper(), shard_index=ind)
        # modify global stat
        shard_dashboard_json["panels"][0]["targets"][0].update(
            {"expr": "count(up{{job=\"{shard}\"}}==1)".format(shard=shard)})
        shard_dashboard_json["panels"][1]["targets"][0].update({"expr": "up{{job=\"{shard}\"}}==0".format(shard=shard)})
        shard_dashboard_json["panels"][1]["targets"][1].update(
            {"expr": "count(up{{job=\"{shard}\"}}==0)".format(shard=shard)})

        id_0 = 4
        title_chart = ""

        for idx in range(ip_array_size):
            ip = ip_array[idx].rstrip()

            if ip == "":
                continue

            if category == "base":
                for part_index in range(4):
                    id_0 += 2

                    x_point = part_index * 6
                    y_point = (idx + 1) * 6 + 2

                    data_part_json = {}

                    # customize title and targets.expr
                    # FIRST COLUMN - CPU Monitoring
                    if part_index == 0:
                        # load cpu metric template
                        data_part_json = copy.deepcopy(dict_part_temp_json["cpu"])

                        # add an alert for CPU
                        data_part_json["alert"]["message"] = "the cpu usage rate of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode, shard_index=ind, ip=ip)
                        # no need alert network
                        if mode not in ["mainnet", "lrtn"]:
                            data_part_json["alert"]["notifications"] = []

                        cpu_query = "100 - (avg by (instance) (irate(node_cpu_seconds_total{{instance=\"{ip}:9100\"," \
                                    "job=\"{shard}\",mode=\"idle\"}}[5m])) * 100)".format(ip=ip, shard=shard)

                        title_chart = "CPU UTILIZATION - "
                        data_part_json["targets"][0].update({"expr": cpu_query})
                    # SECOND COLUMN - RAM Monitoring
                    elif part_index == 1:
                        # load ram metric template
                        data_part_json = copy.deepcopy(dict_part_temp_json["ram"])

                        # add an alert for Memory
                        data_part_json["alert"]["message"] = "the memory usage rate of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode, shard_index=ind, ip=ip)
                        # no need alert network
                        if mode not in ["mainnet", "lrtn"]:
                            data_part_json["alert"]["notifications"] = []

                        ram_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}} - node_memory_" \
                                    "MemFree_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}}) / node_memory_MemTotal_" \
                                    "bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}} * 100".format(ip=ip, shard=shard)

                        ram_actual_usage_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}} - node_memory_" \
                                                 "MemAvailable_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}}) * 100 / node_memory_" \
                                                 "MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip, shard=shard)

                        title_chart = "MEMORY - "
                        data_part_json["targets"][0].update({"expr": ram_query})
                        data_part_json["targets"][1].update({"expr": ram_actual_usage_query})
                    # THIRD COLUMN - DISK Monitoring
                    elif part_index == 2:
                        # load disk metric template
                        data_part_json = copy.deepcopy(dict_part_temp_json["disk"])

                        # add an alert for storage
                        data_part_json["alert"]["message"] = "the free space of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode, shard_index=ind, ip=ip)
                        # no need alert network
                        if mode not in ["mainnet", "lrtn"]:
                            data_part_json["alert"]["notifications"] = []

                        disk_query = "node_filesystem_avail_bytes{{instance=\"{ip}:9100\"," \
                                     "job=\"{shard}\", mountpoint=\"/\"}}/1024/1024/1024".format(ip=ip, shard=shard)

                        title_chart = "FREE SPACE -"

                        data_part_json["targets"][0].update({"expr": disk_query})
                    # FOURTH COLUMN - DISK IO Monitoring
                    elif part_index == 3:
                        # load io metric template
                        data_part_json = copy.deepcopy(dict_part_temp_json["io"])

                        io_read_query = "irate(node_disk_reads_completed_total{{instance=\"{ip}:9100\", job=\"{shard}\"}}[5m])".format(
                            ip=ip, shard=shard)
                        io_write_query = "irate(node_disk_writes_completed_total{{instance=\"{ip}:9100\", job=\"{shard}\"}}[5m])".format(
                            ip=ip, shard=shard)

                        title_chart = "DISK IO - "

                        data_part_json["targets"][0].update({"expr": io_read_query})
                        data_part_json["targets"][1].update({"expr": io_write_query})
                    # FOURTH COLUMN - NETWORK Monitoring
                    # elif part_index == 3:
                    #     # load net metric template
                    #     data_part_json = copy.deepcopy(dict_part_temp_json["net"])
                    #
                    #     # add an alert for network traffic
                    #     data_part_json["alert"]["message"] = "the network traffic of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode, shard_index=ind, ip=ip)
                    #     # no need alert network
                    #     if mode not in ["mainnet", "lrtn"]:
                    #         data_part_json["alert"]["notifications"] = []
                    #
                    #     network_incoming_query = "rate(node_network_receive_bytes_total{{instance" \
                    #                              "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
                    #         ip=ip, shard=shard)
                    #     network_outgoing_query = "rate(node_network_transmit_bytes_total{{instance" \
                    #                              "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
                    #         ip=ip, shard=shard)
                    #
                    #     title_chart = "NETWORK TRAFFIC - "
                    #
                    #     data_part_json["targets"][0].update({"expr": network_incoming_query})
                    #     data_part_json["targets"][1].update({"expr": network_outgoing_query})
                    else:
                        pass

                    data_part_json.update({"gridPos": {'h': 6, 'w': 6, 'x': x_point, 'y': y_point},
                                           "id": id_0,
                                           "title": title_chart + ip
                                           })

                    # insert this chart to dashboard.panels
                    shard_dashboard_json["panels"].append(data_part_json)
            elif category == "network":
                for part_index in range(2):
                    id_0 += 2

                    x_point = part_index * 12
                    y_point = (idx + 1) * 6 + 2

                    data_part_json = {}

                    # customize title and targets.expr
                    # FIRST COLUMN - NETWORK Monitoring
                    if part_index == 0:
                        # load net metric template
                        data_part_json = copy.deepcopy(dict_part_temp_json["net"])

                        # add an alert for network traffic
                        data_part_json["alert"]["message"] = "the network traffic of the {mode} shard{shard_index} node({ip}) is abnormal".format(mode=mode, shard_index=ind, ip=ip)
                        # no need alert network
                        if mode not in ["mainnet", "lrtn"]:
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

                        tcp_alloc = "node_sockstat_TCP_alloc{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip, shard=shard)
                        tcp_inuse = "node_sockstat_TCP_inuse{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip, shard=shard)
                        tcp_mem = "node_sockstat_TCP_mem{{instance=\"{ip}:9100\",job=\"{shard}\"}}".format(ip=ip, shard=shard)

                        title_chart = "TCP SOCK - "
                        data_part_json["targets"][0].update({"expr": tcp_alloc})
                        data_part_json["targets"][1].update({"expr": tcp_inuse})
                        data_part_json["targets"][2].update({"expr": tcp_mem})
                    else:
                        pass

                    data_part_json.update({"gridPos": {'h': 6, 'w': 12, 'x': x_point, 'y': y_point},
                                           "id": id_0,
                                           "title": title_chart + ip
                                           })

                    # insert this chart to dashboard.panels
                    shard_dashboard_json["panels"].append(data_part_json)

        dict_shard_dashboard_json[ind] = shard_dashboard_json
    return dict_shard_dashboard_json


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
        url = grafana_api_host + "dashboards/uid/{mode}_shard{shard_index}_{category}".format(mode=mode, shard_index=index, category=category)
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
    if args.m not in ["all", "mainnet", "lrtn", "test"]:
        raise RuntimeError("need to set correct network mode")
    elif args.m == "all":
        run_modes = ["mainnet", "lrtn"]
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

        # load grafana dashboard template files
        file_path = "grafana_template/dashboard_template.json"
        shard_dashboard_template_json = load_file_to_json(file_path)

        # load latest node ip files
        for index in range(shard_count):
            file_path = "ips/{mode}/shard{shard_index}.txt".format(shard_index=index, mode=mode)
            dict_ip_array[index] = load_file_to_array(file_path)

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
            dict_shard_dashboard_json = create_grafana_config(mode, category, dict_ip_array, shard_dashboard_template_json, dict_part_temp_json)
            logging.info('create grafana config success')

            # update grafana config
            update_grafana_config(mode, category, dict_shard_dashboard_json, grafana_token)
            logging.info('update grafana config success')

    # update prometheus config and restart service
    update_prometheus_config()
    logging.info('update prometheus config success')


if __name__ == "__main__":
    main()
