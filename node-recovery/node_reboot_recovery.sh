#!/bin/bash


systemd_harmony () {
	
	set -eu

	pushd /home/ec2-user

	harmony_service=/etc/systemd/system/harmony.service

	useradd -rs /bin/false harmony

	echo "[*] creating harmony service file .. "
	echo "
[Unit]
Description=harmony service
After=network.target
StartLimitIntervalSec=0

[Service]
Type=simple
Restart=always
RestartSec=1
User=harmony
ExecStart=/home/ec2-user/node.sh -1

[Install]
WantedBy=multi-user.target" > $harmony_service

   systemctl daemon-reload
   systemctl start harmony

   systemctl enable harmony

   popd

}


systemd_harmony