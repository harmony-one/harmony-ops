from collections import defaultdict

import boto3

dict_region_tgarn = defaultdict(list)



# dict for vpc id, 4 most common regions for now, need to add more if necessary
dict_vpc_id = {
    "us-east-1": "vpc-88c9c2f3",
    "us-east-2": "vpc-2c420a44",
    "us-west-1": "vpc-bb770fdc",
    "us-west-2": "vpc-cd3e33b4"
}

def create_target_group(sess, region, target_group_array):

    print("\n==== step 2: creating target group in each region, TargetGroupArn will be stored into dict_region_tgarn \n")
    elbv2_client = sess.client('elbv2', region_name=region)

    # print("Need to target group: ", target_group_array[0])
    try:
        resp = elbv2_client.create_target_group(
            Name=target_group_array[0],
            Protocol='HTTP',
            Port=9500,
            VpcId=dict_vpc_id.get(region),
            HealthCheckProtocol='HTTP',
            HealthCheckPort='traffic-port',
            HealthCheckEnabled=True,
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={
                'HttpCode': '200'
            },
            TargetType='instance'
        )
        # TO-DO:
        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
        print("[INFO] creating target group in region " + region + ", target group name: " + target_group_array[0])
    except Exception as e:
        print("[ERROR] Unexpected error to create the target group: %s" % e)

    # print("Need to target group: ", target_group_array[1])
    try:
        resp = elbv2_client.create_target_group(
            Name=target_group_array[1],
            Protocol='HTTP',
            Port=9800,
            VpcId=dict_vpc_id.get(region),
            HealthCheckProtocol='HTTP',
            HealthCheckPort='traffic-port',
            HealthCheckEnabled=True,
            HealthCheckPath='/',
            HealthCheckIntervalSeconds=30,
            HealthCheckTimeoutSeconds=5,
            HealthyThresholdCount=5,
            UnhealthyThresholdCount=2,
            Matcher={
                'HttpCode': '400'
            },
            TargetType='instance'
        )
        # TO-DO:
        dict_region_tgarn[region].append(resp['TargetGroups'][0]['TargetGroupArn'])
        print("[INFO] creating target group in region " + region + ", target group name: " + target_group_array[1])
    except Exception as e:
        print("[ERROR] Unexpected error to create the target group: %s" % e)

    # TO-DO
    # pp.pprint(dict_region_tgarn)
