# Latest distribution_config.txt can be found at
# https://s3.console.aws.amazon.com/s3/object/harmony-benchmark/logs/2019/06/24/001727/distribution_config.txt?region=us-west-1&tab=overview
# 

create_monitors () {
   cat distribution_config.txt | awk '{print $1,$4}' >  genesis_shard_ip.txt
   while read ip shard
   do  
   curl -X POST -H "Cache-Control: no-cache" -H "Content-Type: application/x-www-form-urlencoded" -d 'api_key='${api_key}'&format=json&type=4&sub_type=99&url='${ip}'&port=6000&friendly_name='${shard}-${ip}'&alert_contacts=0754344_0_0-2840345_0_0' "https://api.uptimerobot.com/v2/newMonitor"
 done < genesis_shard_ip_full.txt

}

#####Main#####

api_key=`cat uptimerobot_api_key.txt`
cat distribution_config.txt | awk '{print $1,$4}' >  genesis_shard_ip.txt
create_monitors

