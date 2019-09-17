#!/bin/bash

sudo yum update -y

prom_config=/etc/prometheus/prometheus.yml
prom_service=/etc/systemd/system/prometheus.service

# download prometheus 2.12.0
curl -LO https://github.com/prometheus/prometheus/releases/download/v2.12.0/prometheus-2.12.0.linux-amd64.tar.gz
tar -xvf prometheus-2.12.0.linux-amd64.tar.gz
mv prometheus-2.12.0.linux-amd64 prometheus-files
rm prometheus-2.12.0.linux-amd64.tar.gz

# create a Prometheus user, required directories, and make prometheus user as the owner of those directories
sudo useradd --no-create-home --shell /bin/false prometheus
sudo mkdir /etc/prometheus
sudo mkdir /var/lib/prometheus
sudo chown prometheus:prometheus /etc/prometheus
sudo chown prometheus:prometheus /var/lib/prometheus

# move prometheus and promtool binary to the proper location, and change ownership
sudo cp prometheus-files/prometheus /usr/local/bin/
sudo cp prometheus-files/promtool /usr/local/bin/
sudo chown prometheus:prometheus /usr/local/bin/prometheus
sudo chown prometheus:prometheus /usr/local/bin/promtool

# move the consoles and console_libraries to the proper location, and change ownership
sudo cp -r prometheus-files/consoles /etc/prometheus
sudo cp -r prometheus-files/console_libraries /etc/prometheus
sudo chown -R prometheus:prometheus /etc/prometheus/consoles
sudo chown -R prometheus:prometheus /etc/prometheus/console_libraries

# create the configuration file, and change ownership
echo "global:
  scrape_interval: 10s
 
scrape_configs:
  - job_name: 'prometheus'
    scrape_interval: 5s
    static_configs:
      - targets: ['localhost:9090']" > $prom_config

sudo chown prometheus:prometheus $prom_config


# create the service file
echo "[Unit]
Description=Prometheus
Wants=network-online.target
After=network-online.target
 
[Service]
User=prometheus
Group=prometheus
Type=simple
ExecStart=/usr/local/bin/prometheus \
    --config.file /etc/prometheus/prometheus.yml \
    --storage.tsdb.path /var/lib/prometheus/ \
    --web.console.templates=/etc/prometheus/consoles \
    --web.console.libraries=/etc/prometheus/console_libraries
 
[Install]
WantedBy=multi-user.target" > $prom_service

# reload the systemd servcie to register prometheus service and start the service
sudo systemctl daemon-reload
sudo systemctl start prometheus

# download grafana v6.3.3
sudo yum install -y https://dl.grafana.com/oss/release/grafana-6.3.3-1.x86_64.rpm

# start the Grafana server
sudo systemctl daemon-reload
sudo systemctl start grafana-server

# enable the systemd service to start at boot
sudo systemctl enable grafana-server.service

