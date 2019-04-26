#!/usr/bin/env python3
import boto3
import sys
import json
import yaml
import pprint

'''

Usage: 	# $python3 main.py <key_ec2_tag> <value_ec2_tag> <wallet.sh>


'''




def main():

	with open("config-test-small.yaml", 'r') as stream:
		try:
			data = yaml.safe_load(stream)
			key = data[0]['key']
			values = data[0]['values']
			document_name = data[0]['document_name']
			source_type = data[0]['source_type']
			owner = data[0]['owner']
			repo = data[0]['repo']
			path = data[0]['path']
			get_options = data[0]['get_options']
			command_line = data[0]['command_line']
		except yaml.YAMLError as exc:
			print(exc)

	# $python3 main.py <key_ec2_tag> <value_ec2_tag> <wallet.sh>
	# Either this command takes all default values, or take values from command line
	if len(sys.argv) > 1:
		key = sys.argv[1]
		values = sys.argv[2]
		command_line = sys.argv[3]


	# parse aws.json to fetch the names of all regions
	regions = []
	with open('aws.json') as f:
		aws_data = json.load(f)
		for i in range(len(aws_data['regions'])):
			regions.append(aws_data['regions'][i]['ext-name'])

	for i in range(len(regions)):
		client_name = 'client_' + regions[i]
		client_name = boto3.client('ssm', region_name=regions[i])
		response = client_name.send_command(Targets=[{"Key": key, "Values": [values, ]}, ], DocumentName=document_name, Parameters={"sourceType": [source_type], "sourceInfo": ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine": [command_line]})


if __name__ == "__main__":
	main()



# AWS did a lousy job to document how to invoke a script from Github on multiple EC2 instances, the following command finally worked after hours of troubleshooting
# response = client.send_command(Targets = [{"Key" : "tag:type", "Values" : ["testnode",]},], DocumentName = "AWS-RunRemoteScript", Parameters = {"sourceType" : ["GitHub"], "sourceInfo" : ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine" : ["nanny.sh"]})
