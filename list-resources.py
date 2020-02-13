""" List all the available EC2 resources in the current account"""

import boto3
import json
import pprint

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

def get_ec2_info(client_ec2):
    """ Retrieve the information about the EC2 instances in a given region

    Arguments:
    client_ec2 - A boto3 client to the ec2 resource for a particular region

    Returns:
    A json object with the information about the instances

    Return structure:
    {
        'Instances':
            {
                'InstanceId':
                {
                    'Platform': '',
                    'PublicIpAddress': '',
                    'PrivateIpAddress': '',
                    'InstanceType': '',
                    'InstanceState': ''
                },
                ...
            }
    }

    """
    instance_info = {}
    ec2_list = client_ec2.describe_instances()
    instance_info['Instances'] = {}
    for reservation in ec2_list['Reservations']:
        for instance in reservation['Instances']:
            instance_info['Instances'][instance['InstanceId']] = {}
            if 'Platform' in instance.keys():
                instance_info['Instances'][instance['InstanceId']]['Platform'] = instance['Platform']
            else:
                instance_info['Instances'][instance['InstanceId']]['Platform'] = "None"
            if 'PublicIpAddress' in instance.keys():
                instance_info['Instances'][instance['InstanceId']]['PublicIpAddress'] = instance['PublicIpAddress']
            else:
                instance_info['Instances'][instance['InstanceId']]['PublicIpAddress'] = "None"
            instance_info['Instances'][instance['InstanceId']]['InstanceState'] = instance['State']['Name']
            instance_info['Instances'][instance['InstanceId']]['InstanceType'] = instance['InstanceType']
            instance_info['Instances'][instance['InstanceId']]['PrivateIpAddress'] = instance['PrivateIpAddress']

    return json.dumps(instance_info)
    #        print(instance['InstanceId'], instance['InstanceType'], instance['Platform'], instance['PrivateIpAddress'], instance['PublicIpAddress'], instance['State'])

if __name__ == '__main__':
    client_ec2 = boto3.client('ec2', region_name='ap-south-1')
    retval = get_ec2_info(client_ec2)
    print(retval)