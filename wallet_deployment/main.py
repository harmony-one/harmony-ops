









#!/usr/bin/env python3
import boto3
import sys
import yaml

with open("config-test-small.yaml", 'r') as stream:
	try:
		# print(yaml.safe_load(stream))
		data = yaml.safe_load(stream)
		region_name = data[0]['region_name']
		key = data[0]['key']
		values = data[0]['values']
		document_name = data[0]['document_name']
		source_type = data[0]['source_type']
		owner = data[0]['owner']
		repo = data[0]['repo']
		path = data[0]['path']
		get_options = data[0]['get_options']
		command_line = data[0]['command_line']

		# print(region_name)
	except yaml.YAMLError as exc:
		print(exc)


client = boto3.client('ssm', region_name=region_name)


# response = client.send_command(InstanceIds = ['i-05af5341989f098d7'], DocumentName = "AWS-RunShellScript", Parameters = {'commands' : ['date']})
# response = client.send_command(Targets = [{"Key" : "tag:type", "Values" : ["testnode",]},], DocumentName = "AWS-RunShellScript", Parameters = {'commands' : ['mkdir /home/ec2-user/ssm_test_Andy']})

# AWS did a lousy job to document how to invoke a script from Github on multiple EC2 instances, the following command finally worked after hours of troubleshooting
# response = client.send_command(Targets = [{"Key" : "tag:type", "Values" : ["testnode",]},], DocumentName = "AWS-RunRemoteScript", Parameters = {"sourceType" : ["GitHub"], "sourceInfo" : ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine" : ["nanny.sh"]})
