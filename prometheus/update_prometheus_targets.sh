#!/bin/bash



# PLEASE update the path to hosts.txt
path_shard="s3://harmony-benchmark/logs/2019/06/24/001727/validator/shard"
# PLEASE update the path to locate the key
path_keys=/Users/andywu/aws/keys


declare -a ip_array0
declare -a ip_array1
declare -a ip_array2
declare -a ip_array3

# retrieve host file
download_hosts_file () {

	for shard_num in {0..3}
	do
		echo "[*] downloading all IP addresses in shard"$shard_num
		aws s3 cp $path_shard"$shard_num"".txt" .		
	done

}

# create an array to store nodes IP addresses
reconstruct_prometheus_config () {

	for shard_num in {0..3}
	do
		while IFS= read -r line; do
			ip_array_temp+=('\"'"$line:9100"'\"','\"'"$line:9091"'\"',)
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
	# scp -i $path_keys/california-key-benchmark.pem prometheus.yml ec2-user@ec2-52-52-168-89.us-west-1.compute.amazonaws.com:/etc/prometheus/prometheus.yml
	scp -i $path_keys/california-key-benchmark.pem prometheus.yml ec2-user@ec2-52-52-168-89.us-west-1.compute.amazonaws.com:~/


}

restart_prometheus_service () {
	systemctl stop prometheus
	systemctl daemon-reload
	systemctl start prometheus
}

download_hosts_file
reconstruct_prometheus_config
update_prometheus_config
# restart_prometheus_service






