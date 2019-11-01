# Harmony Monitor

## Example YAML file
```
# Place all needed authorization keys here
auth:
  pagerduty:
    event-service-key: [key]

target-chain: mainnet

# How often to check, the numbers assumed as seconds
# block-header RPC must happen first
inspect-schedule:
  block-header: 15
  node-metadata: 30

# Port for the HTML report
http-reporter:
  port: 9090

# Numbers assumed as seconds
shard-health-reporting:
  consensus:
    warning: 40
    redline: 300

# Needs to be an absolute file path to usual dump
node-distribution:
  machine-ip-list:
    - .../ip_list1.txt
    - .../ip_list2.txt
```
