""" Retrieves the list of instances using tag key value"""

def instancesWithTag(client, tagKey, tagValue):
    """ Retrieve the list of instances with the given tag key and tag value
    present.
    Usage: instancesWithTag(client, tagKey, tagValue) 
    Parameters: Tag key and value and the client interface
    Return type: list
    Return value: List of instance ids that have tags matching the give key
    value pair"""
    tag_data = client.describe_instances(
        Filters=[
                {
                    'Name': 'tag:' + tagKey,
                    'Values': [
                        tagValue
                ]
            }
        ]
    )

    instanceList = []

    for i in tag_data['Reservations']:
        instanceList.append(i['Instances'][0]['InstanceId'])

    return instanceList 

