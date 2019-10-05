import os
import sys
import boto3
import botocore
from botocore.exceptions import ClientError

EBS_size = 40
BUCKET_NAME = 'harmony-benchmark'
region_array = ['us-east-1', 'us-west-2']

path_file_s3 = 'logs/2019/09/11/005018/'
remote_dist_file = path_file_s3 + 'distribution_config.txt'

home_dir = os.getcwd()
temp_dir = home_dir + '/temp'
try:
    os.mkdir(temp_dir)
except OSError:
    print("Director exists, or creation of this directory %s failed" % temp_dir )
else:
    print("Successfully created this directory %s " % temp_dir)

local_dist_file = temp_dir + '/distribution_config.txt'

dict_ip_per_region = {}
dict_ebs_id_region = {}

session = boto3.Session(profile_name='default')

def download_file_s3(bucketname, remote_file, local_file):
    s3_client = boto3.resource('s3')
    s3_client.Bucket(bucketname).download_file(remote_file, local_file)

def create_ip_for_each_region(fpath):
    if not os.path.isfile(fpath):
        print("File path {} does not exist. Exiting...".format(fpath))
        sys.exit()

    fp = open(fpath)
    line = fp.readline()

    while line:
        if line.rstrip():
            ip = line.split()[0]
            region_num = line.split()[4][0]
            if region_num not in dict_ip_per_region.keys():
                dict_ip_per_region[region_num] = [ip]
            else:
                dict_ip_per_region[region_num].append(ip)
        line = fp.readline()
    fp.close()

def create_ebs_volume_id_each_region(dict_ip):
    for region, ip_array in dict_ip.items():
        if region == '1':
            ec2 = session.client('ec2', region_name = 'us-east-1')
            for ip in ip_array:
                try:
                    resp = ec2.describe_instances(Filters=[{'Name': 'ip-address', 'Values': [ip]}])
                    if len(resp["Reservations"]) != 0:
                        vol_id = resp["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0]["Ebs"]["VolumeId"]
                        if region not in dict_ebs_id_region.keys():
                            dict_ebs_id_region[region] = [vol_id]
                        else:
                            dict_ebs_id_region[region].append(vol_id)
                except ClientError as e:
                    print("Unexpected error: %s" % e)
        elif region == '4':
            ec2 = session.client('ec2', region_name = 'us-west-2')
            for ip in ip_array:
                try:
                    resp = ec2.describe_instances(Filters=[{'Name': 'ip-address', 'Values': [ip]}])
                    if len(resp["Reservations"]) != 0:
                        vol_id = resp["Reservations"][0]["Instances"][0]["BlockDeviceMappings"][0]["Ebs"]["VolumeId"]
                        if region not in dict_ebs_id_region.keys():
                            dict_ebs_id_region[region] = [vol_id]
                        else:
                            dict_ebs_id_region[region].append(vol_id)
                except ClientError as e:
                    print("Unexpected error: %s" % e)
            
def increase_ebs_volume(dict_ebs):
    for region, ebs_id_array in dict_ebs.items():
        if region == '1':
            ec2 = session.client('ec2', region_name = 'us-east-1' )
            for vol_id in ebs_id_array:
                try:
                    resp = ec2.modify_volume(VolumeId = vol_id, Size = EBS_size)
                except ClientError as e:
                    print("Unexpected error: %s" % e)
        if region == '4':
            ec2 = session.client('ec2', region_name = 'us-west-2' )
            for vol_id in ebs_id_array:
                try:
                    resp = ec2.modify_volume(VolumeId = vol_id, Size = EBS_size)
                except ClientError as e:
                    print("Unexpected error: %s" % e)                    

def main():

    download_file_s3(BUCKET_NAME, remote_dist_file, local_dist_file)

    create_ip_for_each_region(local_dist_file)

    create_ebs_volume_id_each_region(dict_ip_per_region)

    increase_ebs_volume(dict_ebs_id_region)


if __name__ == "__main__":
    main()
