set -eu
OS=$(uname -s)
os=$(echo "$OS" | awk '{print tolower($0)}')

# node_exporter version: 0.18.0/2019-05-09
URL_node_exporter_linux=https://github.com/prometheus/node_exporter/releases/download/v0.18.0/node_exporter-0.18.0.linux-amd64.tar.gz

# download and decompress the node exporter in the tmp folder
curl -LO $URL_node_exporter_linux
tar -xvf /tmp/node_exporter-0.18.0.$os-amd64.tar.gz
# add a servcie account for node_exporter
useradd -rs /bin/false node_exporter

# move the node export binary to /usr/local/bin
mv -f /tmp/node_exporter-0.18.0.$os-amd64/node_exporter /usr/local/bin/

# create a node_exporter service file under systemd
node_exporter_service=/etc/systemd/system/node_exporter.service # Linux only
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

systemctl daemon-reload
systemctl start node_exporter

#enable the node exporter servie to the system startup
systemctl enable node_exporte