""" Reads the logs of agent deployment lambdas to determine if the particular 
agent was installed or not. Then, update a dynamo db with the instance id and agent status

"""

import boto3
import logging
import json
import os
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# TODO: change to read the event data
with open(r"C:\Users\abhishek.sharma\Documents\s3_put_object_event_2.json", 'r') as f:
    a = f.read()

a = json.loads(a)

def retrieve_log_file(bucketName, object_key):
    """ Retrieves the log file (object_key) from the given bucket (bucketName)

    Parameters:
    bucketName - name of the S3 bucket from which to retrieve the log file
    object_key - name of the file to be retrieved (along with the prefixes)

    Return:
    bytestream
    """

    try:
        # TODO: Remove the hardcoded creds
        client_s3 = boto3.client(
            's3', 
            aws_access_key_id='AKIAS7PLSXFBO2WZTTCA', 
            aws_secret_access_key='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')
        response = client_s3.get_object(
            Bucket=bucketName,
            Key=object_key,
            RequestPayer='requester'
        )
        return response['Body']
    except Exception as e:
        logger.error("Error in retrieving the log file")
        logger.error(e)
        return None

def check_agent_status(log_file_content):
    """ Checks the contents of the log file to determine whether the agent was installed or not

    Parameters:
    log_file_content - content of the log file

    Return:
    1 - successfully installed
    0 - not installed
    2 - couldn't determine
    3 - others
    """

    # TODO: Go through all the success messages in the installation scripts and fill the below list
    SUCCESS_MESSAGES = ['Agent is installed and in Running Mode !']

    try:
        for message in SUCCESS_MESSAGES:
            if message in log_file_content:
                return 1
            else:
                return 0
    except Exception as e:
        logger.info('Error in determining the agent installation status')
        logger.error(e)
        return 2
    
    return 3

# TODO: Change the context to a positional argument
def lambda_handler(event, context=None):
    # print(event['detail']['requestParameters']['key'])
    object_key = event['detail']['requestParameters']['key']

    # Get the instance id from the key
    #TODO: Search for older instance id
    instance_pattern = re.compile('i-[0-9a-z]{17}')
    instance_id = re.findall(instance_pattern, object_key)[0]
    print(instance_id)

    # Get the Customer ID
    customer_id_pattern = re.compile('/[0-9]{12}/')
    customer_id = re.findall(customer_id_pattern, object_key)[0].strip('/')
    print(customer_id)

    # Get the agent name
    agent_name = None
    AGENTS_LIST = ['AntiMalware', 'Backup', 'Patch', 'Monitoring']
    for i in AGENTS_LIST:
        if i in object_key:
            agent_name = i
    
    if agent_name == None:
        logger.error('Invalid agent name')
        return 0
    else:
        print(agent_name)

    # Get the bucket name
    bucket_name = event['detail']['requestParameters']['bucketName']
    print(bucket_name)

    # Read the file
    log_file_body = retrieve_log_file(bucket_name, object_key)
    if log_file_body is not None:
        log_file_content = log_file_body.read().decode('utf-8')
        agent_status = check_agent_status(log_file_content)
    else:
        logger.error("Couldn't retrieve the log file")
        logger.info('Exiting')
        return 0

    if agent_status == 1:
        print("Agent {0} installed successfully on the instance {1}".format(agent_name, instance_id))

        # TODO: Update the db
    else:
        print("Agent {0} NOT installed successfully on the instance {1}".format(agent_name, instance_id))

        # TODO: Update the db

    return 0

# TODO: remove the explicit call to handler
lambda_handler(a)