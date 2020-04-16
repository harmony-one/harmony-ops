import boto3


# step7 - create entries on Route 53
def create_dns_entries(zone_id, arr_record_set, array_dns_zone):
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
                                    'DNSName': array_dns_zone[0],
                                    'HostedZoneId': array_dns_zone[1],
                                    'EvaluateTargetHealth': True
                                },
                            }
                        },
                    ]
                }
            )
            record_id = resp['ChangeInfo']['Id']
            print("[INFO] creating dns entries in hosted zone " + zone_id + ", name: " + record + ", id:" + record_id)
        except Exception as e:
            print("[ERROR] Unexpected error to create the dns entries: %s" % e)
