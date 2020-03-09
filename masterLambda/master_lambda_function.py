"""
No environment variables (as of now)

Set the timeout according to the normal time of execution of all the Lambda function

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

_continue = True

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
        return (True, response['Status'])
    else:
        return (False, None)

def get_lambda_payload(secretname):
    client_session = boto3.session.Session()
    region = client_session.region_name
    client_secretsmanager = boto3.client('secretsmanager', region_name=region)
    response = client_secretsmanager.get_secret_value(
        SecretId=secretname
    )
    return json.loads(response['SecretString'])

def invoke_lambda_function(client_lambda, function_name, payload):
    if function_name == 'master_lambda_function_2':
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
        payload_to_send = payload
        logger.info('Invoking next instance of master lambda function with the payload data {0}'.format(payload_to_send))
        # invoke another lambda function here with the payload
        function_name = 'master_lambda_function_2'
        invoke_lambda_function(client_lambda, function_name, payload_to_send)
        logging.info("Exiting")
        return False
    else:
        return True

def get_status_command_ids(retval, creds, payload, payload_copy, client_lambda, context, agent_status_data, agent=None):
    _continue = True
    for region in retval.keys():
        client_ssm = boto3.client('ssm', 
            region_name=region, 
            aws_access_key_id=creds[0], 
            aws_secret_access_key=creds[1], 
            aws_session_token=creds[2])
        
        # Add the region key to agent_status_data dict
        agent_status_data[agent][region] = {}
        
        region_data = retval.get(region)
        agent_status_data[agent][region] = {}
        try:
            if type(region_data) is list:
                for instance_data in region_data:
                    if type(instance_data) is dict:
                        # instance_data_keys = instance_data.keys()
                        for instance in instance_data.keys():
                            ssm_command_id = instance_data.get(instance)
                            _st = True
                            match = re.fullmatch(SSM_COMMAND_PATTERN, ssm_command_id)
                            if match:
                                _count = 0
                                _current_command_status = False
                                while not (_current_command_status):
                                    # check the remaining time
                                    _continue = out_of_time(client_lambda, payload_copy, context)
                                    if not _continue:
                                        return False
                                    time.sleep(10)
                                    if _count < 60:
                                        _count += 1
                                    else:
                                        logging.info('Couldn\'t verify the status of command id {0}'.format(ssm_command_id))
                                        _st = False
                                        # pop the command ID as the execution state couldn't be verified
                                        try:
                                            payload_copy['CommandData'][region][region_data.index(instance_data)].pop(instance)
                                        except:
                                            pass
                                        break
                                    _current_command_status = check_ssm_command_status(ssm_command_id, instance, client_ssm)[0]
                                    
                                    if _current_command_status is not None:
                                        if _current_command_status[1] == 'TimedOut':
                                            agent_status_data[agent][region][instance] = 2
                                        elif _current_command_status[1] == 'Success':
                                            agent_status_data[agent][region][instance] = 1
                                        else:
                                            agent_status_data[agent][region][instance] = 0
                                
                                # pop the command ID if it exists and the execution has finished or timedout
                                try:
                                    logger.info("Removing the data for {0}".format(instance))
                                    payload_copy['CommandData'][region][region_data.index(instance_data)].pop(instance)
                                except:
                                    pass
                                if _st:
                                    logging.info('Command ID {0} execution finished'.format(ssm_command_id))
                            else:
                                # If the data for instance id is not a valid SSM command ID
                                agent_status_data[agent][region][instance] = 0
                try:
                    logger.info("Removing command data for region {0}".format(region))
                    payload_copy['CommandData'].pop(region)
                    logger.info("Command data is now: {0}".format(payload_copy['CommandData']))
                except:
                    pass
            else:
                logger.info("Removing the empty region field for region {0}".format(region))
                payload_copy['CommandData'].pop(region)
        except Exception as e:
            logger.info('Error in parsing information for region {0}'.format(region))
            logger.error(e)
    # Test the validity
    logger.info("CommandData is now {0}".format(payload_copy["CommandData"]))
    logger.info("Removing the CommandData section from the payload")
    payload_copy.pop("CommandData")
    return True

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

    # Initialize agent_status_data dict
    agent_status_data = {}
    
    try:
        if 'CommandData' in _payload.keys():
            if len(list(_payload['CommandData'].keys())) == 0:
                logger.info("CommandData is empty. Removing it.")
                _payload.pop('CommandData')
                logger.info("Current payload is {0}".format(_payload))
            # Pop the CommandData if it contains only agent name
            elif len(list(_payload['CommandData'].keys())) == 1 and list(_payload['CommandData'].keys())[0] == 'AgentName':
                logger.info("CommandData is empty. Removing it.")
                _payload.pop('CommandData')
                logger.info("Current payload is {0}".format(_payload))
            else:
                retval = _payload.get("CommandData")
                get_status_command_ids(retval, creds, _payload, _payload_copy, client_lambda, context, agent_status_data, agent=_payload.get("CommandData").get("AgentName"))
        
        for agent in _payload.keys():
            if agent != 'CommandData' and agent != 'MasterLambda':
                _agent_data = json.dumps(_payload.get(agent)).encode()
                function_name = AGENT2FUNCTION[agent]
                agent_status_data[agent] = {}
                logger.info("Agent status data is {0}".format(agent_status_data))
                logger.info(_agent_data)
                
                # Call another method to invoke agent installer lambda
                res = invoke_lambda_function(client_lambda, function_name, _agent_data)
                streaming_body = res['Payload']
                retval = json.loads(streaming_body.read().decode('utf-8'))
                _payload_copy['CommandData'] = copy.deepcopy(retval)
                
                # Add the agent name to the command data
                _payload_copy['CommandData']['AgentName'] = agent
                
                # Add the agent status data to the payload for next invocation
                # Should we move it to the end??
                _payload_copy['AgentStatusData'] = agent_status_data
                
                # VERY IMPORTANT!!! Prevents the Lambda function from infinitely invoking itself
                logger.info("Removing data for {0} agent".format(agent))
                _payload_copy.pop(agent)
                logger.info("Payload copy now contains data for agents: {0}".format(_payload_copy.keys()))
                if not get_status_command_ids(retval, creds, _payload, _payload_copy, client_lambda, context, agent_status_data, agent=agent):
                    logger.info("Ran out of time.")
                    return True #Exit the execution of Lambda function
                    
    except Exception as e:
        logger.info("Exiting due to the below error")
        logger.error(e)
    logger.info('Payload contains the data: {0}'.format(_payload_copy))
    logger.info('Calling the parser function')
    # Call the agent status parser function
    invoke_lambda_function(client_lambda, 'agent_data_parser', json.dumps(_payload_copy['AgentStatusData']).encode())
    return True