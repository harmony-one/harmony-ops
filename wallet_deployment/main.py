#!/usr/bin/env python3
from argparse import ArgumentParser

import boto3
import json
import yaml
import argparse
import ast
import pprint
import time
'''

Usage: 	# $python3 main.py <key_ec2_tag> <value_ec2_tag> <wallet.sh>


cmd for testing
python3 main.py -k tag:type -v testnode -d AWS-RunRemoteScript -s GitHub -o bwu2sfu -r harmony-ops -f aws/ssm -b branch:master -c nanny.sh -a aws.json
python3 main.py -k tag:Name -v 4-banjo-od-2019-04-30_22_14_16 -d AWS-RunRemoteScript -s GitHub -o bwu2sfu -r harmony-ops -f aws/ssm -b branch:master -c deploy_wallet.sh -a aws.json
'''




def main():

	parser = argparse.ArgumentParser()
	parser.add_argument('-p', '--profile', help = 'preset configuration files for different testing', required = False)
	parser.add_argument('-k', '--key', help = 'key of the tag attached to the EC2 instance', required = False)
	parser.add_argument('-v', '--value', help='value of the tag attached to the EC2 instance', required = False)
	parser.add_argument('-d', '--document', help='document name', required = False)
	parser.add_argument('-s', '--source', help='source type', required = False)
	parser.add_argument('-o', '--owner', help='owner of the repo', required=False)
	parser.add_argument('-r', '--repo', help='name of the repository', required=False)
	parser.add_argument('-f', '--folder', help='path to the folder storing bash script', required=False)
	parser.add_argument('-b', '--branch', help='branch', required=False)
	parser.add_argument('-c', '--command', help='script to be executed', required=False)
	parser.add_argument('-a', '--awsjson', help='json file to define aws regions', required=False)

	args = vars(parser.parse_args())

	# if the profile yaml file is given, parse the file
	if args['profile']:
		with open(args['profile'], 'r') as stream:
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

	else:
		key = args['key']
		values = args['value']
		document_name = args['document']
		source_type = args['source']
		owner = args['owner']
		repo = args['repo']
		path = args['folder']
		get_options = args['branch']
		command_line = args['command']


	# parse aws.json to fetch the names of all regions
	aws_file = ''
	if args['awsjson']:
		aws_file = args['awsjson']
	else:
		aws_file = 'aws.json'

	regions = []
	with open(aws_file) as f:
		aws_data = json.load(f)
		for i in range(len(aws_data['regions'])):
			regions.append(aws_data['regions'][i]['ext-name'])

	for i in range(len(regions)):
	# for i in range(2):
		
		try:
			print("----")
			print("creating a SSM client in region: " + regions[i])
			client_ssm_name = 'client_ssm_' + regions[i]
			# print(client_ssm_name)
			client_ssm_name = boto3.client('ssm', region_name=regions[i])

			print("creating a EC2 client in region: " + regions[i])
			client_ec2_name = 'client_ec2' + regions[i]
			client_ec2_name = boto3.client('ec2', region_name=regions[i])
			tag_filter = [{
				'Name' : key,
				'Values' : []
			}]
			tag_filter[0]["Values"].append(values)

			ec2_resp_name = 'resp_ec2' + regions[i]
			ec2_resp_name = client_ec2_name.describe_instances(Filters=tag_filter)

			print("total number of test nodes: " + str(len(ec2_resp_name["Reservations"])))

			# print("key: " + key)
			# print("values: " + values)
			# print("source type: " + source_type)
			# print("document name: " + document_name)
			# print("owner: " + owner)
			# print("repo: " + repo)
			# print("path: " + path)
			# print("get_options: " + get_options)
			# print("command_line: " + command_line)
			# print()


			target_dict = {
				"Key" : "",
				"Values" : []
			}
			target_dict["Key"] = key
			target_dict["Values"].append(values)

			target_array = []
			target_array.append(target_dict)

			# print("TARGET ARRAY")
			# print(target_array)


			# POC
			para_dict = {
				"sourceType" : [],
				"sourceInfo" : [],
				"commandLine" : []
			}


			para_dict["sourceType"].append(source_type)
			para_dict["commandLine"].append(command_line)

			info_json = {
				"owner" : owner,
				"repository" : repo,
				"path" : path,
				"getOptions" : get_options

			}

			para_dict["sourceInfo"].append(json.dumps(info_json))

			# ref_string = '{"sourceType" : ["GitHub"],"sourceInfo" : ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\",\"getOptions\":\"branch:master\"}"],"commandLine" : ["nanny.sh"]}'
			# print(ref_string)

			# response = client_name.send_command(Targets=[{"Key": key, "Values": [values, ]}, ], DocumentName=document_name, Parameters={"sourceType": [source_type], "sourceInfo": ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine": [command_line]})
			# response = client_name.send_command(Targets = target_array, DocumentName = document_name, Parameters = ast.literal_eval(para_string))

			# FUNCTIONAL CMD
			# response = client_name.send_command(Targets=[{"Key": "tag:type", "Values": ["testnode", ]}, ], DocumentName="AWS-RunRemoteScript", Parameters={"sourceType": ["GitHub"], "sourceInfo": ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine": ["nanny.sh"]})
			print("Invoking script stored in GitHub in region " + regions[i])
			ssm_resp_name = 'resp_ssm' + regions[i]
			# print(target_array)
			# print(document_name)
			# print(para_dict)
			ssm_resp_name = client_ssm_name.send_command(Targets=target_array, DocumentName=document_name, Parameters=para_dict, MaxErrors='100%')
			pprint.pprint(ssm_resp_name)


			print("----")
			time.sleep(1)
		except Exception as e:
			raise e 
		else:
			print('------------- succeded ---------------------')


if __name__ == "__main__":
	main()



# AWS did a lousy job to document how to invoke a script from Github on multiple EC2 instances, the following command finally worked after hours of troubleshooting
# response = client_name.send_command(Targets = [{"Key" : "tag:type", "Values" : ["testnode",]},], DocumentName = "AWS-RunRemoteScript", Parameters = {"sourceType" : ["GitHub"], "sourceInfo" : ["{\"owner\" : \"bwu2sfu\", \"repository\":\"harmony-ops\", \"path\":\"aws/ssm\", \"getOptions\":\"branch:master\"}"],"commandLine" : ["nanny.sh"]})






















