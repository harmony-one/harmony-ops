### AWS Cloud

#### SystemD Configuration (/etc/systemd/system/go-aws-ec2.service)
```text
[Unit]
Description=go-aws-ec2
After=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=1
User=ubuntu
Group=ubuntu
WorkingDirectory=/opt/apps/go-aws-ec2
ExecStart=/opt/apps/go-aws-ec2/go-aws-ec2 --client-ip client-ip.json
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
```

### Digital Ocean Cloud

#### OAuth Configuration (configuration.json)

```text
1. Login Digital Ocean and Create OAuth Client Application
2. configure "configuration.json"
  2.1 homeUri
  2.2 redirectUri
  2.3 clientId
  2.4 clientSecret
```

#### SystemD Configuration (/etc/systemd/system/go-digital-ocean-droplet.service)
```text
[Unit]
Description=go-digital-ocean-droplet
After=network-online.target

[Service]
Type=simple
Restart=always
RestartSec=1
User=root
Group=root
WorkingDirectory=/opt/apps/go-digital-ocean-droplet
ExecStart=/opt/apps/go-digital-ocean-droplet/go-digital-ocean-droplet --client-ip client-ip.json --configuration configuration.json
StartLimitInterval=0

[Install]
WantedBy=multi-user.target
```
