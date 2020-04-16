import boto3

from helpers import *

def register_explorers(region, arr_instance_id, d_region_tgarn):
    """
    register explorer nodes into the corresponding target group
        * register the same target into tg-https and tg-wss
    depends on:
        * dict_region_tgarn
        *
    """
    print("\n==== step 6:  registering explorer instances into the target group \n")
    elbv2_client = boto3.client('elbv2', region_name=region)

    # array_of_exp_shard = parse_network_config(region + '-exp-' + str(j))
    # array_instance_id_exp = retrieve_instance_id(array_of_exp_shard)

    # REGISTER each instance_id into the TWO target groups
    for instance in arr_instance_id:
        try:
            # register targets into tg-s[i]-api-pga-https
            resp = elbv2_client.register_targets(
                TargetGroupArn=d_region_tgarn[region][0],
                Targets=[
                    {
                        'Id': instance,
                        'Port': 9500,
                    },
                ]
            )
            # register targets into tg-s[i]-api-pga-wss
            resp2 = elbv2_client.register_targets(
                TargetGroupArn=d_region_tgarn[region][1],
                Targets=[
                    {
                        'Id': instance,
                        'Port': 9800,
                    },
                ]
            )
            print("[INFO] registering an explorer node into TWO target groups (tg-https and tg-wss) in region " + region)
        except Exception as e:
            print("[ERROR] Unexpected error to create the listener: %s" % e)
