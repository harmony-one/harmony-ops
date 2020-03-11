import pprint
import boto3
from collections import defaultdict


dict_region_sslcerts = defaultdict(list)


pp = pprint.PrettyPrinter(indent=4)

# step 1: request SSL certificates
def request_ssl_certificates(region, dn):
    """
    Notes:
        * idempotent ops
        * store CertificateArn to dict_region_sslcerts
    """

    print("\n==== step 1: request SSL certificates, CertificateArn will be stored into dict_region_sslcerts \n")
    acm_client = boto3.client(service_name='acm', region_name=region)
    try:
        resp = acm_client.request_certificate(
            DomainName=dn,
            ValidationMethod='DNS',
            IdempotencyToken='112358',
        )
        dict_region_sslcerts[region].append(resp['CertificateArn'])
        print("--creating ssl certificate in region " + region + " for domain name " + dn)
        print(dn + ': ' + resp['CertificateArn'])
    except Exception as e:
        print("Unexpected error to request certificates: %s" % e)
