""" Start RDS instances that match a given pair of tag key and tag value

    Usage: python3 startRDSInstance.py <region> <tagKey> <tagValue> <topicArn>
"""

import boto3
import sys

import retrieveRDSInstancesByTags
import sendSNSMessage

region = sys.argv[1]
tagKey = sys.argv[2]
tagValue = sys.argv[3]
topicArn = sys.argv[4]

def startRDSInstance(tagKey, tagValue, region, topicArn):
    """ Start the RDS instances that match the given tag key and tag value in
    the given region

    Note: Not applicable to:
        1. RDS already running
        2. Multi AZ RDS
        3. RDS with Aurora engine

    Return: Returns a list of list of instance id and current db instance
    status or a message if the request would not have been successful
    """

    client_rds = boto3.client('rds', region_name=region)

    instanceList = retrieveRDSInstancesByTags.retrieveRDSInstancesByTags(client_rds, tagKey, tagValue)

    message = []

    for i in instanceList:
        if i[2] is True or i[3] is True:
            message.append([i[1], 'Cant start RDS instance; maybe it is AWS Aurora or Multi AZ or already stopped'])
        else:
            try:
                response = client_rds.start_db_instance(
                    DBInstanceIdentifier=i[1],
                    )
                message.append([i[1], response['DBInstance']['DBInstanceStatus']])
            except:
                message.append([i[1], 'Cant start RDS instance'])


#    return message
    
    sns_client = boto3.client('sns', region_name=region) 
    sendSNSMessage.sendSNSMessage(sns_client, topicArn, str(message))


startRDSInstance(tagKey, tagValue, region, topicArn)
