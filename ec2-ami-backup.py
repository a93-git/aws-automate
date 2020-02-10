"""
Take AMI backup of all the EC2 instances that have matching tags.

Following environment variables need to be provided:
Tag_Key: Tag key to look for
Tag_Value: Tag value corresponding to the above tag key
SNS_Topic: SNS topic ARN to send the notification to

Note: The SNS topic __MUST__ exist in the same region where this Lambda function is created

Create and attach the following policies to the Lambda role to enable the script to create image and send SNS
notifications

// EC2 access

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": [
                "ec2:DescribeInstances",
                "ec2:DescribeTags",
                "ec2:CreateImage"
            ],
            "Resource": "*"
        }
    ]
}

// SNS access

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "sns:Publish",
            "Resource": "arn:aws:sns:ap-southeast-1:630125610951:s247_topic"
        }
    ]
}

"""

import boto3
import os
import datetime
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))


class Backup():
    tag_key = os.environ['Tag_Key']
    tag_value = os.environ['Tag_Value']

    def __init__(self, region):
        self.region = region
        self.client_ec2 = boto3.client('ec2', region_name=self.region)

    def find_matching_vm(self):
        """ Find VMs matching the tag key and tag value"""
        try:
            matching_vms = self.client_ec2.describe_instances(
                Filters=[
                    {
                        'Name': 'tag:{0}'.format(self.tag_key),
                        'Values': [self.tag_value]
                    }
                ]
            )
            return matching_vms
        except Exception as e:
            logger.info("Error in getting the instance details")
            logger.error(e)
            logger.info("Region is {0}".format(self.region))
            return None
        
    def take_ami_backup(self, client_ec2, instance_id):
        """ Take AMI backup of an EC2 instance"""
        ami_id = self.client_ec2.create_image(
            DryRun=False,
            NoReboot=True,
            InstanceId=instance_id,
            Name="{0}-{1}".format(instance_id, datetime.datetime.now().strftime("%Y-%m-%d-%H-%M"))
        )
        
        return ami_id


def send_notification(message):
    """ Send SNS notification"""
    client_session = boto3.session.Session()
    region = client_session.region_name
    
    client_sns = boto3.client('sns', region_name=region)
    
    sns_arn = os.environ['SNS_Topic']
    
    message_id = client_sns.publish(
        TopicArn=sns_arn,
        Message="The AMIs created are as follows: \n{0}".format(message),
        Subject = "AMIs created on {0}".format(datetime.datetime.now().strftime("%Y-%m-%d"))
        )
        
    return message_id

def lambda_handler(event, context):
    message_instance_details = {}
    
    for region in REGIONS.values():
        message_instance_details[region] = []
        backup_obj = Backup(region)
        matching_vms = backup_obj.find_matching_vm()
    
        if matching_vms is not None:
            for reservation in matching_vms['Reservations']:
                for instance in reservation['Instances']:
                    ami_id = backup_obj.take_ami_backup(backup_obj.client_ec2, instance['InstanceId'])
                    message_instance_details[region].append({instance['InstanceId']: ami_id['ImageId']})
                    
    message_id = send_notification(message_instance_details)
    logger.info("Message ID is {0}".format(message_id['MessageId']))