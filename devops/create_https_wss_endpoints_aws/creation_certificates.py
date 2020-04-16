import pprint
import boto3
from collections import defaultdict


dict_region_sslcerts    = defaultdict(list)
dict_exist_sslcerts     = defaultdict(list)

pp = pprint.PrettyPrinter(indent=4)

# step 1: request SSL certificates
def request_ssl_certificates(sess, region, dn):
    """
    Notes:
        * idempotent ops
        * store CertificateArn to dict_region_sslcerts
    """
    acm_client = sess.client(service_name='acm', region_name=region)
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

def get_existing_certs(sess, region, dn):

    acm_client = sess.client(service_name='acm', region_name=region)
    dict_exist_sslcerts.clear()
    try:
        resp = acm_client.list_certificates(
            CertificateStatuses=['ISSUED', 'PENDING_VALIDATION'],
            MaxItems=1000,
        )
        for cert in resp['CertificateSummaryList']:
            if dn == cert['DomainName']:
                dict_exist_sslcerts[cert['DomainName']].append(cert['CertificateArn'])

        # pp.pprint(dict_exist_sslcerts)
        return dict_exist_sslcerts
    except Exception as e:
        print("Unexpected error to get exist certificates: %s" % e)
