import pprint
import boto3
from collections import defaultdict

dict_region_sslcerts = defaultdict(list)

pp = pprint.PrettyPrinter(indent=4)


# step 1: request SSL certificates
def request_ssl_certificates(region, dn, dict_exist_sslcerts):
    """
    Notes:
        * idempotent ops
        * store CertificateArn to dict_region_sslcerts
    """

    print("\n==== step 1: request SSL certificates, CertificateArn will be stored into dict_region_sslcerts \n")
    # skip if certificate already exist
    if dn in dict_exist_sslcerts:
        dict_region_sslcerts[region].append(dict_exist_sslcerts[dn])
        print("--certificate already exist, skip\n")
    else:
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


# get the list of current exist ssl certificates
def get_exist_ssl_certificates(region):
    dict_exist_sslcerts = {}
    acm_client = boto3.client(service_name='acm', region_name=region)

    try:
        resp = acm_client.list_certificates(
            CertificateStatuses=['PENDING_VALIDATION', 'ISSUED'],
            MaxItems=1000,
        )
        certificate_count = len(resp['CertificateSummaryList'])
        # TODO: need to handle cases where the number of returns exceeds 1000
        if certificate_count > 0:
            for i in range(certificate_count):
                certificate_item = resp['CertificateSummaryList'][i]
                dict_exist_sslcerts[certificate_item['DomainName']] = certificate_item['CertificateArn']

        return dict_exist_sslcerts
    except Exception as e:
        print("Unexpected error to get exist certificates: %s" % e)
