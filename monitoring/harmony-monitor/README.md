# Harmony Monitor

## Example YAML file
```yaml
# Place all needed authorization keys here
auth:
  pagerduty:
    event-service-key: YOUR_PAGERDUTY_KEY

network-config:
  target-chain: testnet
  public-rpc: 9500

# How often to check, the numbers assumed as seconds
# block-header RPC must happen first
inspect-schedule:
  block-header: 15
  node-metadata: 30

# Number of concurrent go threads sending HTTP requests
# Time in seconds to wait for the HTTP request to succeed
performance:
  num-workers: 32
  http-timeout: 1

# Port for the HTML report
http-reporter:
  port: 8080

# Numbers assumed as seconds
shard-health-reporting:
  consensus:
    warning: 70

# Needs to be an absolute file path
# NOTE: The ending of the basename of the file
# is important, in this example the 0, 1, 2, 3
# indicate shardID. Need to have some trailing
# number on the filename
node-distribution:
  machine-ip-list:
  - /home/ec2-user/mainnet/shard0.txt
  - /home/ec2-user/mainnet/shard1.txt
  - /home/ec2-user/mainnet/shard2.txt
  - /home/ec2-user/mainnet/shard3.txt
```
