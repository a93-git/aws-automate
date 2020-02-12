""" Find the instance name for the given instance id. """

def getInstanceName(client, instanceId):
    """ Find the name of the instance for the given instance ID. 
    Note: The name of the instance is retrieved from the 'Name' tag 
    
    Return value: List of tuples containing (instanceId, instanceName)
    Return type: List"""

    instanceName = client.describe_instances(
        Filters=[
            {
                'Name': 'instance-id',
                'Values': [
                    instanceId
                ]
            }
        ]
    )

    instanceList = []
    for i in instanceName['Reservations'][0]['Instances'][0]['Tags']:
        if 'Name' == str(i['Key']):
            instanceList.append((instanceId, i['Value']))

    return instanceList

