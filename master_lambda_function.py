""" One function to rule them all

No environment variables (as of now)

Set the timeout according to the normal time of execution of all the Lambda function

TODO Implement a state function - tracks the current state of execution of all the four Lambda functions
TODO Check for remaining execution time on a regular interval
TODO If timeout occurs, call subsequent Lambda function with current state

Note: Now we need to add the following policy to the cross-account-role in Customer's environment

ssm:GetInvocationStatus
"""

import boto3
import json
import time
import logging
import re

logger = logging.getLogger()
logger.setLevel(logging.INFO)

AGENT_NAMES = ["Site24x7", "DesktopCentral", "TrendMicro", "Commvault"]
FUNCTION_NAMES = ["x_account_site247_installer", "x_account_dc_installer", "x_account_dsm_installer", "x_account_commvault_installer"]
AGENT2FUNCTION = dict(zip(AGENT_NAMES, FUNCTION_NAMES))

SSM_COMMAND_PATTERN = re.compile(r'\b([a-z0-9]+-){4}[a-z0-9]{12}\b')

def get_temp_creds(role_arn, external_id):
    """ Retrieve temporary security credentials

    Arguments:
    role_arn - ARN of the AWS role to assume (in the customer's account)
    external_id - An alphanumeric string configured as an added security measure

    Return:
    Returns a tuple of access key, secret access key and session token
    """
    logger.info("Getting temporary access credentials for Role ARN {0}".format(role_arn))
    try:
        client_sts = boto3.client('sts')
        a = client_sts.assume_role(RoleSessionName='test-session', RoleArn=role_arn, DurationSeconds=900, ExternalId=external_id)
        access_key = a['Credentials']['AccessKeyId']
        secret_access_key = a['Credentials']['SecretAccessKey']
        session_token = a['Credentials']['SessionToken']
        return (access_key, secret_access_key, session_token)
    except Exception as e:
        logger.info("Error in getting temporary security credentials")
        logger.error(e)
        return (None, None, None)

def check_ssm_command_status(ssm_command_id, instance, client_ssm):
    response = client_ssm.get_command_invocation(
        CommandId=ssm_command_id,
        InstanceId=instance
    )

    if response['Status'] == 'TimedOut' or response['Status'] == 'Success' or response['Status'] == 'Failed':
        return True
    else:
        return False

def get_lambda_payload():
    """ Read the lambda payload file"""

    logging.info("Attempting to read the file...")
    with open("./master_lambda_input.json", "r") as f:
        a = f.read()
    
    try:
        return json.loads(a)
    except Exception as e:
        logging.info("Can't read the payload file")
        logging.error(e)
        logging.info("Nothing to do. Exiting the lambda execution now.")
        exit()
    
def lambda_handler(event, context):

    _time = time.time()

    # Retrieve the current region name
    client_session = boto3.session.Session()
    region = client_session.region_name

    _payload = get_lambda_payload()

    client_lambda = boto3.client('lambda', region_name=region)

    _master_lambda_data = _payload.get('MasterLambda')
    _payload.pop("MasterLambda")
    
    role_arn = _master_lambda_data.get('Role_ARN')
    external_id = _master_lambda_data.get('External_Id')
    creds = get_temp_creds(role_arn, external_id)

    for agent in _payload.keys():
        _agent_data = json.dumps(_payload.get(agent)).encode()
        function_name = AGENT2FUNCTION[agent]

        res = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=_agent_data
            )
        
        streaming_body = res['Payload']
        retval = json.loads(streaming_body.read().decode('utf-8'))

        for region in retval.keys():
            client_ssm = boto3.client('ssm', 
                region_name=region, 
                aws_access_key_id=creds[0], 
                aws_secret_access_key=creds[1], 
                aws_session_token=creds[2])

            region_data = retval.get(region)

            try:
                if type(region_data) is list:
                    for instance_data in region_data:
                        if type(instance_data) is dict:
                            for instance in instance_data.keys():
                                ssm_command_id = instance_data.get(instance)
                                match = re.fullmatch(SSM_COMMAND_PATTERN, ssm_command_id)
                                if match:
                                    _count = 0
                                    while not (check_ssm_command_status(ssm_command_id, instance, client_ssm)):
                                        time.sleep(10)
                                        if _count < 12:
                                            _count += 1
                                        else:
                                            logging.info('Couldn\'t verify the status of command id {0}'.format(ssm_command_id))
                                            break
                                    logging.info('Command ID {0} execution finished'.format(ssm_command_id))
            except Exception as e:
                logger.info('Error in parsing information for region {0}'.format(region))
                logger.error(e)

        remaining_time = context.get_remaining_time_in_millis()

        if remaining_time < 60000:
            logging.info("Out of time")
            logging.info("Invoking next instance of Lambda function")
            logging.info("Exit")

    return remaining_time