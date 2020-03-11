# TO-DO:

import boto3


def create_dns_entries(zond_id, arr_record_set):
    client = boto3.client('route53')
    for record in arr_record_set:
        response = client.change_resource_record_sets(
            HostedZoneId=zond_id,
            ChangeBatch={
                'Changes': [
                    {
                        'Action': 'CREATE',
                        'ResourceRecordSet': {
                            'Name': record,
                            'Type': 'A',
                            'AliasTarget': {
                                'HostedZoneId': 'string',
                                'DNSName': 'string',
                                'EvaluateTargetHealth': True
                            },
                        }
                    },
                ]
            }
        )
