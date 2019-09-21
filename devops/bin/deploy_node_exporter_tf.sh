#!/usr/bin/env bash

# latest node_exporter version: 0.18.1/2019-06-04
URL_node_exporter_linux=https://github.com/prometheus/node_exporter/releases/download/v0.18.1/node_exporter-0.18.1.linux-amd64.tar.gz

# download and decompress the node exporter in the tmp folder
echo "downloading node_exporter ..."
curl -LO $URL_node_exporter_linux


echo "unzipping the file ..."
tar -xvf node_exporter-*.tar.gz
echo "moving node_exporter to the proper place ..."
mv -f node_exporter-*-amd64/node_exporter /usr/local/bin/
echo "cleaning up ..."
rm node_exporter-*.tar.gz
rm -r node_exporter-*-amd64/

# add a servcie account for node_exporter
echo "adding user node_exporter ..."
id -u node_exporter &>/dev/null || sudo useradd -rs /bin/false node_exporter

# create a node_exporter service file under systemd
node_exporter_service=/etc/systemd/system/node_exporter.service
echo "creating node exporter service file ..."
echo "[Unit]
   Description=Node Exporter
   After=network.target
   [Service]
   User=node_exporter
   Group=node_exporter
   Type=simple
   ExecStart=/usr/local/bin/node_exporter
   [Install]
   WantedBy=multi-user.target" >$node_exporter_service

sudo systemctl daemon-reload
sudo systemctl start node_exporter

#enable the node exporter servie to the system startup
sudo systemctl enable node_exporter