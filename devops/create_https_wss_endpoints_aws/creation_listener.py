

import boto3
from collections import defaultdict

dict_region_ListenerArn = defaultdict(list)

def create_listener(sess, region, d_region_elb2arn, d_region_sslcerts, d_region_tgarn):
    """
    depends on:
        * dict_region_elb2arn
        * dict_region_sslcerts
        * dict_region_tgarn
    """
    print("\n==== step 4: creating https listener on the created elb2, ListenerArn will be stored into dict_region_ListenerArn \n")
    elbv2_client = sess.client('elbv2', region_name=region)

    try:
        resp = elbv2_client.create_listener(
            LoadBalancerArn=d_region_elb2arn[region][0],
            Protocol='HTTPS',
            Port=443,
            SslPolicy='ELBSecurityPolicy-2016-08',
            Certificates=[{'CertificateArn': d_region_sslcerts[region][0]}],
            DefaultActions=[
                {
                    'Type': 'forward',
                    # tg-s[i]-api-pga-https
                    'TargetGroupArn': d_region_tgarn[region][0],
                    'ForwardConfig': {
                        'TargetGroups': [
                            {
                                # tg-s[i]-api-pga-https
                                'TargetGroupArn': d_region_tgarn[region][0],
                                'Weight': 1
                            },
                        ],
                        'TargetGroupStickinessConfig': {
                            'Enabled': False,
                        }
                    }
                },
            ]
        )
        dict_region_ListenerArn[region].append(resp['Listeners'][0]['ListenerArn'])
        print("[INFO] creating https listener with attaching ssl certificat in region " + region + ", LoadBalancerArn: " + d_region_elb2arn[region][0])
    except Exception as e:
        print("[ERROR] Unexpected error to create the listener: %s" % e)
