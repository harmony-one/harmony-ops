# TO-DO:

import boto3


# step7 - create entries on Route 53
def create_dns_entries(zone_id, arr_record_set, region_elb2_dns_name):
    print("\n==== step 7: create entries on Route 53 \n")
    client = boto3.client('route53')
    for record in arr_record_set:
        try:
            resp = client.change_resource_record_sets(
                HostedZoneId=zone_id,
                ChangeBatch={
                    'Changes': [
                        {
                            'Action': 'UPSERT',
                            'ResourceRecordSet': {
                                'Name': record,
                                'Type': 'A',
                                'AliasTarget': {
                                    'HostedZoneId': zone_id,
                                    'DNSName': region_elb2_dns_name,
                                    'EvaluateTargetHealth': True
                                },
                            }
                        },
                    ]
                }
            )
            record_id = resp['ChangeInfo']['Id']
            print("--creating dns entries in hosted zone " + zone_id + ", name: " + record + ", id:" + record_id)
        except Exception as e:
            print("Unexpected error to create the dns entries: %s" % e)
