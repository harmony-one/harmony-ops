# Harmony Monitor

## Example YAML file
```yaml
# Place all needed authorization keys here
auth:
  pagerduty:
    event-service-key: YOU_REPLACE_ME

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

# Needs to be an absolute file path
# NOTE: The ending of the basename of the file
# is important, in this example the 0, 1, 2, 3
# indicate shardID. Needed to have some trailing 
# number on the filename
node-distribution:
  machine-ip-list:
    - /home/ec2-user/mainnet/shard0.txt
    - /home/ec2-user/mainnet/shard1.txt
    - /home/ec2-user/mainnet/shard2.txt
    - /home/ec2-user/mainnet/shard3.txt
```
