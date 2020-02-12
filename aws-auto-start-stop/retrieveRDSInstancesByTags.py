""" Retrieve the DB instance identifier for RDS instances that have matching
tag key and value pair """

def retrieveRDSInstancesByTags(client, tagKey, tagValue):
    """ Retrieves the list of RDS instances that have a matching tag key and
    value pair

    Parameters: client to RDS service, a tag key and value
    Return: A list of tuple of DB arn, DB instance identifier, a boolean value representing if it has
    'aurora' in its engine name and a boolean value representing if it is
    multi AZ
    Note: Multi AZ instances can't be stopped/started
    """

    response = client.describe_db_instances()

    rdsList = []

    # Retrieve the list of all the available db instances in the current region
    for i in response['DBInstances']:
        rdsList.append((i['DBInstanceArn'], i['DBInstanceIdentifier'], 'aurora' in i['Engine'] or 'Aurora' in i['Engine'], i['MultiAZ']))

    returnRdsList = []

    # Filter the db instances that have the given tag key and value
    for i in rdsList:
        tagData = client.list_tags_for_resource(ResourceName=i[0])
        for tag in tagData['TagList']:
            if tag['Key'] == tagKey and tag['Value'] == tagValue:
                    returnRdsList.append(i)

    return returnRdsList

