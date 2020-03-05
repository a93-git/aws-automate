""" One function to rule them all

No environment variables (as of now)

Set the timeout according to the normal time of execution of all the Lambda function

DONE Implement a state function - tracks the current state of execution of all the four Lambda functions
DONE Check for remaining execution time on a regular interval
DONE If timeout occurs, call subsequent Lambda function with current state

Note: Now we need to add the following policy to the cross-account-role in Customer's environment

ssm:GetInvocationStatus

In the Lambda role, add the ARN of the master role as well so that it can invoke itself

Change the function names in the FUNCTION_NAMES list 
"""

import boto3
import json
import time
import logging
import re
import copy

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
    logger.info('Checking status of command id {0}'.format(ssm_command_id))
    response = client_ssm.get_command_invocation(
        CommandId=ssm_command_id,
        InstanceId=instance
    )

    if response['Status'] == 'TimedOut' or response['Status'] == 'Success' or response['Status'] == 'Failed':
        return True
    else:
        return False

def get_lambda_payload(secretname):
    client_session = boto3.session.Session()
    region = client_session.region_name
    client_secretsmanager = boto3.client('secretsmanager', region_name=region)
    response = client_secretsmanager.get_secret_value(
        SecretId=secretname
    )
    return json.loads(response['SecretString'])

def invoke_lambda_function(client_lambda, function_name, payload):
    if function_name == 'master_lambda_function':
        res = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType='Event',
            Payload=json.dumps(payload).encode()
            )
    else:
        res = client_lambda.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',
            Payload=payload
            )
    return res

def out_of_time(client_lambda, payload, context):
    remaining_time = int(context.get_remaining_time_in_millis())
    if remaining_time < 60000:
        # invoke another lambda function here with the payload
        logging.info("Out of time")
        logging.info("Invoking next instance of master lambda function")
        function_name = 'master_lambda_function'
        invoke_lambda_function(client_lambda, function_name, payload)
        logging.info("Exit")
        exit()
    else:
        pass

def get_status_command_ids(retval, creds, payload, payload_copy, client_lambda, context):
    for region in retval.keys():
        client_ssm = boto3.client('ssm', 
            region_name=region, 
            aws_access_key_id=creds[0], 
            aws_secret_access_key=creds[1], 
            aws_session_token=creds[2])

        region_data = retval.get(region)
        region_data_copy = copy.deepcopy(region_data)
        try:
            if type(region_data) is list:
                for instance_data in region_data:
                    if type(instance_data) is dict:
                        # instance_data_keys = instance_data.keys()
                        for instance in instance_data.keys():
                            ssm_command_id = instance_data.get(instance)
                            match = re.fullmatch(SSM_COMMAND_PATTERN, ssm_command_id)
                            if match:
                                _count = 0
                                while not (check_ssm_command_status(ssm_command_id, instance, client_ssm)):
                                    # check the remaining time
                                    out_of_time(client_lambda, payload_copy, context)
                                    time.sleep(5)
                                    if _count < 24:
                                        _count += 1
                                    else:
                                        logging.info('Couldn\'t verify the status of command id {0}'.format(ssm_command_id))
                                        # pop the command ID as the execution state couldn't be verified
                                        try:
                                            payload_copy['CommandData'][region][region_data.index(instance_data)].pop(instance)
                                        except:
                                            pass
                                        break
                                # pop the command ID if it exists and the execution has finished
                                try:
                                    payload_copy['CommandData'][region][region_data.index(instance_data)].pop(instance)
                                except:
                                    pass
                                logging.info('Command ID {0} execution finished'.format(ssm_command_id))
        except Exception as e:
            logger.info('Error in parsing information for region {0}'.format(region))
            logger.error(e)
            raise

        out_of_time(client_lambda, payload_copy, context)

def lambda_handler(event, context):

    _time = time.time()

    # Retrieve the current region name
    client_session = boto3.session.Session()
    region = client_session.region_name

    # Get the payload
    if type(event) != dict:
        secret_name = event
        _payload = get_lambda_payload(secret_name)
        # Dictionary changed size during runtime fix
        _payload_copy = copy.deepcopy(_payload)
    else:
        _payload = event
        # Dictionary changed size during runtime fix
        _payload_copy = copy.deepcopy(_payload)

    logger.info(_payload)
    client_lambda = boto3.client('lambda', region_name=region)

    _master_lambda_data = _payload.get('MasterLambda')
    
    role_arn = _master_lambda_data.get('Role_ARN')
    external_id = _master_lambda_data.get('External_Id')
    creds = get_temp_creds(role_arn, external_id)

    if 'CommandData' in _payload.keys():
        retval = _payload.get("CommandData")
        get_status_command_ids(retval, creds, _payload, _payload_copy, client_lambda, context)
    
    for agent in _payload.keys():
        time.sleep(60)
        if agent != 'CommandData' and agent != 'MasterLambda':
            _agent_data = json.dumps(_payload.get(agent)).encode()
            function_name = AGENT2FUNCTION[agent]
            logger.info(_agent_data)
            
            # Call another method to invoke agent installer lambda
            res = invoke_lambda_function(client_lambda, function_name, _agent_data)
            
            streaming_body = res['Payload']
            
            retval = json.loads(streaming_body.read().decode('utf-8'))
    
            _payload_copy['CommandData'] = copy.deepcopy(retval)
            get_status_command_ids(retval, creds, _payload, _payload_copy, client_lambda, context)
            
    return True