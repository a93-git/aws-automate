""" One function to rule them all

No environment variables (as of now)

Set the timeout according to the normal time of execution of all the Lambda function

TODO Implement a state function - tracks the current state of execution of all the four Lambda functions
TODO Check for remaining execution time on a regular interval
TODO If timeout occurs, call subsequent Lambda function with current state
"""

import boto3
import json
import time
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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

def lambda_handler(event, context):
    # Retrieve the current region name
    client_session = boto3.session.Session()
    region = client_session.region_name

    # Payload to be passed on by the Cloudwatch rule
    _payload = '{ "Activation_Key": "eu_1b673cc3b4bc93137f5a3a2655d9df23", "Role_ARN": "arn:aws:iam::879633881541:role/swo_x_account_role", "Output_S3_Bucket": "swo-agent-logs", "Output_S3_Key_Prefix_Windows": "customer4/commvault/windows", "Output_S3_Key_Prefix_Linux": "customer4/commvault/linux", "Tag_Key": "swoMonitor", "Tag_Value": "1", "External_Id": "57a2d9d9-37f0-4435-aadf-1257142f2bcc", "SNS_Topic": "arn:aws:sns:ap-southeast-1:205041875266:lambda_notification" }'
    _payload = _payload.encode()

    client_lambda = boto3.client('lambda', region_name=region)

    role_arn = "arn:aws:iam::879633881541:role/swo_x_account_role"
    external_id = "57a2d9d9-37f0-4435-aadf-1257142f2bcc"
    creds = get_temp_creds(role_arn, external_id)

    res = client_lambda.invoke(
        FunctionName='x_account_site247_installer',
        InvocationType='RequestResponse',
        Payload=_payload,
        )
    
    streaming_body = res['Payload']
    retval = json.loads(streaming_body.read().decode('utf-8'))

    try:
        for region in retval.keys():
            client_ssm = boto3.client('ssm', 
                region_name=region, 
                aws_access_key_id=creds[0], 
                aws_secret_access_key=creds[1], 
                aws_session_token=creds[2])
            region_data = retval.get(region)
            if type(region_data) is list:
                for instance_data in region_data:
                    if type(instance_data) is dict:
                        for instance in instance_data.keys():
                            ssm_command_id = instance_data.get(instance)
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
        logger.info('Error in parsing command information')
        logger.error(e)

    remaining_time = context.get_remaining_time_in_millis()

    return remaining_time