#!/bin/bash

source /Users/bwu2/.github/token.sh

path_shard0="https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/shard0.txt"
path_shard1="https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/shard1.txt"
path_shard2="https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/shard2.txt"
path_shard3="https://raw.githubusercontent.com/harmony-one/nodedb/master/mainnet/shard3.txt"

# PLEASE update the path to locate the key
path_keys=/Users/andywu/aws/keys


declare -a ip_array0
declare -a ip_array1
declare -a ip_array2
declare -a ip_array3

# retrieve host file
download_hosts_file () {

	# download list of IP for shard 0
	curl -H "Authorization: token $git_token" \
	-o shard0.txt $path_shard0

	# download list of IP for shard 1
	curl -H "Authorization: token $git_token" \
	-o shard1.txt $path_shard1

	# download list of IP for shard 2
	curl -H "Authorization: token $git_token" \
	-o shard2.txt $path_shard2

	# download list of IP for shard 3
	curl -H "Authorization: token $git_token" \
	-o shard3.txt $path_shard3

}

# create an array to store nodes IP addresses
reconstruct_prometheus_config () {

	for shard_num in {0..3}
	do
		while IFS= read -r line; do
			ip_array_temp+=('\"'"$line:9100"'\"',)
		done < shard${shard_num}.txt
		declare -a ip_array"$shard_num"="(${ip_array_temp[*]})"


		unset ip_array_temp
	done

	# might want to put this in the loop..
	array_size0=${#ip_array0[*]}
	last_ip0=${ip_array0[$array_size0-1]}
	last_ip_comma_removed0=${last_ip0%?}
	ip_array0[$array_size0-1]=$last_ip_comma_removed0

	array_size1=${#ip_array1[*]}
	last_ip1=${ip_array1[$array_size1-1]}
	last_ip_comma_removed1=${last_ip1%?}
	ip_array1[$array_size1-1]=$last_ip_comma_removed1

	array_size2=${#ip_array2[*]}
	last_ip2=${ip_array2[$array_size2-2]}
	last_ip_comma_removed2=${last_ip2%?}
	ip_array2[$array_size2-1]=$last_ip_comma_removed2


	array_size3=${#ip_array3[*]}
	last_ip3=${ip_array3[$array_size3-3]}
	last_ip_comma_removed3=${last_ip3%?}
	ip_array3[$array_size3-1]=$last_ip_comma_removed3

	echo "[*] reconstructing prometheus.yml .. "
	echo "
global:
  scrape_interval: 10s

scrape_configs:
  - job_name: 'shard0'
    scrape_interval: 5s
    static_configs:" > prometheus.yml

	echo "      - targets: ["${ip_array0[*]}"]" >> prometheus.yml

	echo "
  - job_name: 'shard1'
    scrape_interval: 5s
    static_configs:" >> prometheus.yml

	echo "      - targets: ["${ip_array1[*]}"]" >> prometheus.yml

	echo "
  - job_name: 'shard2'
    scrape_interval: 5s
    static_configs:" >> prometheus.yml

	echo "      - targets: ["${ip_array2[*]}"]" >> prometheus.yml

	echo "
  - job_name: 'shard3'
    scrape_interval: 5s
    static_configs:" >> prometheus.yml

	echo "      - targets: ["${ip_array3[*]}"]" >> prometheus.yml	


}


update_prometheus_config () {

	echo "[*] Overwritting prometheus.yml .. "
	# sudo scp -i $path_keys/california-key-benchmark.pem prometheus.yml ec2-user@ec2-52-52-168-89.us-west-1.compute.amazonaws.com:/etc/prometheus/prometheus.yml
	scp -i $path_keys/california-key-benchmark.pem prometheus.yml ec2-user@ec2-52-52-168-89.us-west-1.compute.amazonaws.com:~/

}

restart_prometheus_service () {
	sudo systemctl stop prometheus
	sudo systemctl daemon-reload
	sudo systemctl start prometheus
	sudo systemctl enable prometheus
}

download_hosts_file
reconstruct_prometheus_config
update_prometheus_config
# restart_prometheus_service

