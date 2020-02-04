import boto3
import os
import urllib.request
import logging

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))
CSV_URL = os.environ['csv_url']
DATA = urllib.request.urlopen(CSV_URL)

with open(os.getcwd() + '/' + 'csv_data', 'wb') as f:
    f.write(DATA.readline())

def lambda_handler(event, context):
    for region in REGIONS.values():
        ec2_client = boto3.client('ec2', region_name=region)
        tag_resources(ec2_client, DATA)

        # Detect MAC, DOS or Unix line endings
        with open('csv_data', 'rb') as f:
            if "\r\n" in f.read():
                newline = '\r\n'    # DOS
            elif "\r" in f.read():
                newline = '\r'  # MAC
            else:
                newline = '\n'  # UNIX

        # Tag keys and values are retrieved on the fly, no need to hardcode
        with open('csv_data', 'r', newline=newline) as f:
            a = f.readline()
            if a:
                tag_keys = a.split(',')
            while True:
                a = f.readline()
                if a:
                    tagging_data, counter = {}, 0
                    b = a.split(',')
                    try:
                        for key in tag_keys:
                            tagging_data[key] = b[counter]
                            counter = counter + 1
                    except Exception as e:
                        logging.info("Error occured while retrieving tag values")
                        logging.error(e)
                    tag_resources(ec2_client, tagging_data)
                else:
                    break

def tag_resources(ec2_client, tagging_data):
    instance_id = tagging_data.pop('instance_id')
    tags = [{x: y} for x, y in (tagging_data.items())]

    ec2_client.create_tags(
        Resources=[instance_id],
        Tags = tags
    )