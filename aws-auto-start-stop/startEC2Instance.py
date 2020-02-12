"""Starts EC2 Instances that have a given set of Tag Key and Tag Value
    
    Usage: python3 startEC2Instance.py <region> <tagKey> <tagValue> <topicArn>
"""

import boto3
import sys

import retrieveEC2InstancesByTags
import sendSNSMessage

region = sys.argv[1]
tagKey = sys.argv[2]
tagValue = sys.argv[3]
topicArn = sys.argv[4]

def startInstances(tagKey, tagValue, region, topicArn):
    """ Start the instances that have the 'tagKey:tagValue' pair 

    Parameters: tagKey and tagValue
    Output: Prints a list of tuple of currentstate, instance id and previous
    state of all the matching instances
    """
    # Create an interface with AWS EC2 service
    client_ec2 = boto3.client('ec2', region_name=region)
    
    # Retrieve the list of instances that have the above tag
    instancesWithTag = retrieveEC2InstancesByTags.instancesWithTag(client_ec2,
    tagKey, tagValue)

    message = []
    # Start the instances in the above list
    if len(instancesWithTag) == 0:
        message.append('No instances found matching the above criteria')
    else:
        try:
            # Start instances
            response = client_ec2.start_instances(
            InstanceIds=instancesWithTag,
            DryRun=False
            )
            for i in response['StartingInstances']:
                message.append((i['CurrentState']['Name'], i['InstanceId'], i['PreviousState']['Name']))
        except:
            message.append('Can\'t start instances')

    sns_client = boto3.client('sns', region_name=region)
    sendSNSMessage.sendSNSMessage(sns_client, topicArn, str(message))

startInstances(tagKey, tagValue, region, topicArn)
