# Install fluent-bit
See for Amazon Linux: https://docs.fluentbit.io/manual/installation/redhat_centos

# Configure it

## td-agent-bit.conf
```ini
[SERVICE]
    Flush 1
    Daemon Off
    Log_Level warning
    Parsers_File parsers.conf
    HTTP_Server Off

[INPUT]
    Name tail
    Tag harmony
    Path /home/ec2-user/latest/validator-*.log
    Skip_Long_Lines On
    DB /home/ec2-user/harmony.db
    DB.Sync Off
    Parser harmony

[FILTER]
    Name grep
    Match *
    Regex msg BINGO

[OUTPUT]
    Name es
    Match *
    tls On
    tls.verify Off
    Host search-<your es endpoint>.us-east-1.es.amazonaws.com
    Port 443
    Index harmony
    Type bingo
    Generate_ID On
```

## parsers.conf
```ini
[PARSER]
    Name harmony
    Format json
    Time_Key t
    Time_Format %Y-%m-%dT%H:%M:%S.%LZ
    Types ViewID:integer
```

# Amazon Elasticsearch Service

# Configure Kibana
Create monitor, trigger and destination
I configured my trigger to alert when there is less than 1 BINGO in the last minute
For destination I used AWS SNS: https://docs.aws.amazon.com/elasticsearch-service/latest/developerguide/alerting.html
