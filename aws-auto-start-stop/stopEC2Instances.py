""" Stops EC2 Instances that have a given set of Tag Key and Tag Value
    
    Usage: python3 stopEC2Instances.py <region> <tagKey> <tagValue> <topicArn>
"""

import boto3
import sys

import sendSNSMessage
import retrieveEC2InstancesByTags

region = sys.argv[1]
tagKey = sys.argv[2]
tagValue = sys.argv[3]
topicArn = sys.argv[4]

def stopInstances(tagKey, tagValue, region, topicArn):
    """ Stop the instances that have the 'tagKey:tagValue' pair 

    Parameters: tagKey and tagValue
    Output: Prints a list of tuple of current state, instance id and previous
    state of all the matching instances
    """
    # Create an interface with AWS EC2 service
    client_ec2 = boto3.client('ec2', region_name=region)

    # Retrieve the list of instances that have the above tag
    instancesWithTag = retrieveEC2InstancesByTags.instancesWithTag(client_ec2,
    tagKey, tagValue)

    message = []
    # Stop the instances in the above list
    if len(instancesWithTag) == 0:
        message.append('No instances found matching the above criteria')
    else:
        try:
            # Start instances
            response = client_ec2.stop_instances(
            InstanceIds=instancesWithTag,
            DryRun=False
            )
            for i in response['StoppingInstances']:
                message.append((i['CurrentState']['Name'], i['InstanceId'], i['PreviousState']['Name']))
        except:
            message.append('Error in stopping instances')
    sns_client = boto3.client('sns', region_name=region)
    sendSNSMessage.sendSNSMessage(sns_client, topicArn, str(message))

stopInstances(tagKey, tagValue, region, topicArn)
