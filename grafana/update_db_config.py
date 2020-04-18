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
}


def shcmd(cmd, ignore_error=False):
    print('Doing:', cmd)
    ret = subprocess.call(cmd, shell=True)
    print('Returned', ret, cmd)
    if ignore_error is False and ret != 0:
        raise RuntimeError("Failed to execute {}. Return code:{}".format(
            cmd, ret))
    return ret


# get latest node ips from github
def download_ip_list_from_github(git_token, mode):
    # download list of IP from shard, and save it to file
    for index in range(shard_count):
        url_path = "https://raw.githubusercontent.com/harmony-one/nodedb/" \
                   "master/{mode}/shard{shard_index}.txt".format(shard_index=index, mode=mode)
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
def create_grafana_config(mode, dict_ip_array, shard_dashboard_template_json, dict_part_temp_json):
    dict_shard_dashboard_json = {}
    for ind in range(shard_count):
        ip_array = dict_ip_array.get(ind)
        ip_array_size = len(ip_array)

        shard = "shard{shard_index}_{mode}".format(shard_index=ind, mode=mode)
        db_shard = "db_shard{shard_index}_{mode}.json".format(shard_index=ind, mode=mode)

        shard_dashboard_json = copy.deepcopy(shard_dashboard_template_json)
        # modify dashboard uid
        shard_dashboard_json["uid"] = "{mode}_shard{shard_index}_basenode".format(mode=mode, shard_index=ind)
        # modify dashboard title
        shard_dashboard_json["title"] = "Harmony Nodes Monitoring - {mode} - SHARD {shard_index}".format(
            mode=mode.upper(), shard_index=ind)
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

                    cpu_query = "100 - (avg by (instance) (irate(node_cpu_seconds_total{{instance=\"{ip}:9100\"," \
                                "job=\"{shard}\",mode=\"idle\"}}[5m])) * 100)".format(ip=ip, shard=shard)

                    title_chart = "CPU UTILIZATION - "
                    data_part_json["targets"][0].update({"expr": cpu_query})
                # SECOND COLUMN - RAM Monitoring
                elif part_index == 1:
                    # load ram metric template
                    data_part_json = copy.deepcopy(dict_part_temp_json["ram"])

                    # add an alert for OOM
                    data_part_json["alert"]["conditions"][0]["evaluator"]["params"][0] = int(max_actual_usage_memory_rate)
                    data_part_json["alert"]["message"] = "{mode} shard{shard_index} node({ip}) is out of " \
                                                         "memory".format(mode=mode, shard_index=ind, ip=ip)

                    ram_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}} - node_memory_" \
                                "MemFree_bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}}) / node_memory_MemTotal_" \
                                "bytes{{instance=\"{ip}:9100\",job=\"{shard}\"}} * 100".format(ip=ip, shard=shard)

                    ram_actual_usage_query = "(node_memory_MemTotal_bytes{{instance=\"{ip}:9100\"}} - node_memory_" \
                                             "MemAvailable_bytes{{instance=\"{ip}:9100\"}}) * 100 / node_memory_" \
                                             "MemTotal_bytes{{instance=\"{ip}:9100\"}}".format(ip=ip)

                    title_chart = "MEMORY - "
                    data_part_json["targets"][0].update({"expr": ram_query})
                    data_part_json["targets"][1].update({"expr": ram_actual_usage_query})
                # THIRD COLUMN - DISK Monitoring
                elif part_index == 2:
                    # load disk metric template
                    data_part_json = copy.deepcopy(dict_part_temp_json["disk"])

                    # add an alert for low storage
                    data_part_json["alert"]["conditions"][0]["evaluator"]["params"][0] = int(min_storage_space)
                    data_part_json["alert"]["message"] = "{mode} shard{shard_index} node({ip}) is out of " \
                                                         "disk space".format(mode=mode, shard_index=ind, ip=ip)

                    disk_query = "node_filesystem_avail_bytes{{instance=\"{ip}:9100\"," \
                                 "job=\"{shard}\", mountpoint=\"/\"}}/1024/1024/1024".format(ip=ip, shard=shard)

                    title_chart = "FREE SPACE -"

                    data_part_json["targets"][0].update({"expr": disk_query})
                # FOURTH COLUMN - NETWORK Monitoring
                elif part_index == 3:
                    # load net metric template
                    data_part_json = copy.deepcopy(dict_part_temp_json["net"])

                    network_incoming_query = "rate(node_network_receive_bytes_total{{instance" \
                                             "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
                        ip=ip, shard=shard)
                    network_outgoing_query = "rate(node_network_transmit_bytes_total{{instance" \
                                             "=\"{ip}:9100\", job=\"{shard}\", device=\"eth0\"}}[5m]) / 1024".format(
                        ip=ip, shard=shard)

                    title_chart = "NETWORK TRAFFIC - "

                    data_part_json["targets"][0].update({"expr": network_incoming_query})
                    data_part_json["targets"][1].update({"expr": network_outgoing_query})
                else:
                    pass

                data_part_json.update({"gridPos": {'h': 6, 'w': 6, 'x': x_point, 'y': y_point},
                                       "id": id_0,
                                       "title": title_chart + ip
                                       })

                # insert this chart to dashboard.panels
                shard_dashboard_json["panels"].append(data_part_json)

        dict_shard_dashboard_json[ind] = shard_dashboard_json

        with open("grafana/dashboards/{mode}/".format(mode=mode) + db_shard, 'w') as fp:
            json.dump(shard_dashboard_json, fp)

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
def update_grafana_config(mode, dict_shard_dashboard_json, grafana_token):
    for index in range(shard_count):
        # get now dashboard version
        url = grafana_api_host + "dashboards/uid/{mode}_shard{shard_index}_basenode".format(mode=mode,
                                                                                            shard_index=index)
        headers = {"Authorization": "Bearer " + grafana_token}
        response = requests.get(url, headers=headers).json()
        version = response["dashboard"]["version"]

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
        "disk": load_file_to_json("grafana_template/disk_template.json"),
        "net": load_file_to_json("grafana_template/net_template.json")
    }

    # get script run mode
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', type=str, help="select run mode. mainnet ostn stn etc.")
    args = parser.parse_args()
    if args.m not in ["all", "mainnet", "ostn", "stn", "test"]:
        raise RuntimeError("need to set run mode")
    elif args.m == "all":
        run_modes = ["mainnet", "ostn", "stn"]
    else:
        run_modes = [args.m]

    # update for each mode network
    for i, mode in enumerate(run_modes):
        # special shard count for stn & test
        if mode in ["stn"]:
            shard_count = 2
        elif mode in ["test"]:
            shard_count = 1

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

        # create grafana whole config file
        dict_shard_dashboard_json = create_grafana_config(mode, dict_ip_array, shard_dashboard_template_json,
                                                          dict_part_temp_json)
        logging.info('create grafana config success')

        # create prometheus whole config file
        create_prometheus_config(mode, dict_ip_array, prometheus_config_template)
        logging.info('create prometheus config success')

        # update grafana config
        update_grafana_config(mode, dict_shard_dashboard_json, grafana_token)
        logging.info('update grafana config success')

    # update prometheus config and restart service
    update_prometheus_config()
    logging.info('update prometheus config success')


if __name__ == "__main__":
    main()
