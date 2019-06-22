  #!/bin/bash
echo shard view date-time ip
for s in {0..3}; do 
#for s in 2; do
  echo
  pssh -i -h <(grep "validator $s" distribution_config.txt | cut -d' ' -f1) -x '-i key1 -i key4 -o GlobalKnownHostsFile=/dev/null -o UserKnownHostsFile=/dev/null -o StrictHostKeyChecking=no' -l ec2-user "tac ../tmp_log/*/* | egrep -m1 'BINGO|HOORAY'" | \
    grep ViewID | \
    python -c $'import datetime, sys, json;\nfor x in sys.stdin:\n y = json.loads(x); print "%s %7s %s %s" % (sys.argv[1], y.get("ViewID", str(y.get("myViewID", 0))), datetime.datetime.strftime(datetime.datetime.strptime(y["t"][:-4], "%Y-%m-%dT%H:%M:%S.%f") + datetime.timedelta(hours=-7), "%m/%d-%H:%M:%S.%f"), y["ip"])' $s | \
    sort -k3
done