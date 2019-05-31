#!/usr/bin/env bash

# ----------------------------------------------------------------------
# 	[Author] Andy Bo Wu
#         	A bash script to deploy Prometheus and Grafana on a Linux box
# -----------------------------------------------------------------------


# -----------------------------------------------------------------------
#	[Version]
#			* 2019/05/30 created the initial script 	
#			*
#	
#		 
# 	[Notes]
#			* make sure port 9090 is open for Prometheus
#			* make sure port 3000 is open for Grafana
# -----------------------------------------------------------------------


setup_prometheus(){

	useradd --no-create-home --shell /bin/false prometheus
	mkdir /etc/prometheus
	mkdir /var/lib/prometheus

	chown prometheus:prometheus /etc/prometheus
	chown prometheus:prometheus /var/lib/prometheus


	# download prometheus v2.10.0, released on 2019/05/25
	curl -LO https://github.com/prometheus/prometheus/releases/download/v2.10.0/prometheus-2.10.0.linux-amd64.tar.gz
	tar -xvf prometheus-2.10.0.linux-amd64.tar.gz
	mv prometheus-2.10.0.linux-amd64 prometheus-files

	cp prometheus-files/prometheus /usr/local/bin/
	cp prometheus-files/promtool /usr/local/bin/
	chown prometheus:prometheus /usr/local/bin/prometheus
	chown prometheus:prometheus /usr/local/bin/promtool


	cp -r prometheus-files/consoles /etc/prometheus
	cp -r prometheus-files/console_libraries /etc/prometheus
	chown -R prometheus:prometheus /etc/prometheus/consoles
	chown -R prometheus:prometheus /etc/prometheus/console_libraries

	# create the prometheus config file
	touch /etc/prometheus/prometheus.yml
	# write the followign content the the config file
	echo "global:
  	scrape_interval: 10s
 
	scrape_configs:
	  - job_name: 'prometheus'
	    scrape_interval: 5s
	    static_configs:
	      - targets: ['localhost:9090']" >> /etc/prometheus/prometheus.yml
	#[TO-DO] need to set targets as a argument



	# change the ownership of the above file to user prometheus
	chown prometheus:prometheus /etc/prometheus/prometheus.yml

	# deploy and launch prometheus as a service
	touch /etc/systemd/system/prometheus.service
	# write the following content to the prometheus service file
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
	WantedBy=multi-user.target" >> /etc/prometheus/prometheus.yml 


	# launch the service
	systemctl daemon-reload
	systemctl start prometheus

	# cmd to check service status: $systemctl status prometheus
	# or, on web UI: http://<prometheus-ip>:9090/graph

}

setup_grafana(){

	cd /tmp 
	wget https://dl.grafana.com/oss/release/grafana_6.2.1_amd64.deb
	apt-get install -y adduser libfontconfig 
	dpkg -i grafana_6.2.1_amd64.deb 

	systemctl start grafana-server
	systemctl enable grafana-server


	# on web UI: http://<grafana_IP>:3000

}





































