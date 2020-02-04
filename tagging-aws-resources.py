import boto3
import os
import urllib.request
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

#REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
#REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
#REGIONS = dict(zip(REGION_NAMES, REGION_CODES))
CSV_URL = os.environ['csv_url']
DATA = urllib.request.urlopen(CSV_URL)

with open('/tmp/csv_data.csv', 'wb') as f:
    f.write(DATA.read())

def tag_resources(tagging_data):
    print(tagging_data)
    instance_id = tagging_data.pop('instance_id')
    region = tagging_data.pop('region')

    # Create a dictionary with tag keys and values
    tags = [{'Key': x, 'Value' : y} for x, y in (tagging_data.items())]

    logger.info(tags)
    # Create the client for the given region
    ec2_client = boto3.client('ec2', region_name=region)

    # Tag the resources
    ec2_client.create_tags(
        Resources=[instance_id],
        Tags = tags
    )

def lambda_handler(event, context):
    # for region in REGIONS.values():
    #     ec2_client = boto3.client('ec2', region_name=region)
    #     tag_resources(ec2_client, DATA)

    # Detect MAC, DOS or Unix line endings
    with open('/tmp/csv_data.csv', 'rb') as f:
        test_value = f.read()
        if b"\r\n" in test_value:
            newline = '\r\n'    # DOS
        elif b"\r" in test_value:
            newline = '\r'  # MAC
        else:
            newline = '\n'  # UNIX

    # Tag keys and values are retrieved on the fly, no need to hardcode
    with open('/tmp/csv_data.csv', 'r', newline=newline) as f:

        # Get the headers of the file
        headers = f.readline()
        if headers:
            tag_keys = [x.strip() for x in headers.split(',')]
        
        # Read till the end of the file
        while True:
            a = f.readline()
            if a:
                tagging_data, counter = {}, 0
                # Remove extra whitespaces
                b = [x.strip() for x in a.split(',')]
                try:
                    # Create a dict of the keys and their corresponding values
                    for key in tag_keys:
                        tagging_data[key] = b[counter]
                        counter = counter + 1
                except Exception as e:
                    logger.info("Error occured while retrieving tag values")
                    logger.error(e)
                tag_resources(tagging_data)
            else:
                break