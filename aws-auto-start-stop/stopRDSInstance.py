""" Stop RDS instances that match a given pair of tag key and tag value
    
    Usage: python3 stopRDSInstance.py <region> <tagKey> <tagValue> <topicArn>
"""

import boto3
import sys
import datetime

import retrieveRDSInstancesByTags
import sendSNSMessage

region = sys.argv[1]
tagKey = sys.argv[2]
tagValue = sys.argv[3]
topicArn = sys.argv[4]

def stopRDSInstance(tagKey, tagValue, region, topicArn):
    """ Stop the RDS instances that match the given tag key and tag value in
    the given region

    Note: Not applicable to:
        1. RDS already stopped
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
            message.append([i[1], 'Cant stop RDS instance; maybe it is AWS Aurora or Multi AZ or already stopped'])
        else:
            snapshot_identifier = i[1] + '-boto3-snap-' + datetime.datetime.now().strftime('%Y-%m-%d-%H-%M')
            try:
                response = client_rds.stop_db_instance(
                    DBInstanceIdentifier=i[1],
                    DBSnapshotIdentifier=snapshot_identifier
                    )
                message.append([i[1], response['DBInstance']['DBInstanceStatus']])
            except:
                message.append([i[1], 'Cant stop RDS instance'])


#    return message
    
    sns_client = boto3.client('sns', region_name=region) 
    sendSNSMessage.sendSNSMessage(sns_client, topicArn, str(message))

stopRDSInstance(tagKey, tagValue, region, topicArn)
