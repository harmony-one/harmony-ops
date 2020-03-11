import boto3


def create_rule(region, d_region_ListenerArn, d_region_tgarn, d_region_elb2arn, header_value):
    """


    """
    print("\n==== step 5: creating a customized rule such that traffic will be forwarded to tg-s[i]-api-pga-wss "
          "when host is ws.s[i].pga.hmny.io \n")
    # deliberately use index instead of obj to retrieve array item, this index needs to be reused to retrieve
    elbv2_client = boto3.client('elbv2', region_name=region)

    try:
        resp = elbv2_client.create_rule(
            ListenerArn=d_region_ListenerArn[region][0],
            Conditions=[
                {
                    'Field': 'host-header',
                    'Values': [
                        header_value,
                    ],
                },
            ],
            Priority=1,
            Actions=[
                {
                    'Type': 'forward',
                    'TargetGroupArn': d_region_tgarn[region][1],
                    'ForwardConfig': {
                        'TargetGroups': [
                            {
                                'TargetGroupArn': d_region_tgarn[region][1],
                                'Weight': 1
                            },
                        ],
                        'TargetGroupStickinessConfig': {
                            'Enabled': False,
                            'DurationSeconds': 1
                        }
                    }
                },
            ]
        )
        print("--creating a customized elb2 rule in region " + region + " for LoadBalancerArn: " + d_region_elb2arn[region][0])
    except Exception as e:
        print("Unexpected error to create the listener: %s" % e)
