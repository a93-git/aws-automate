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

def check_ssm_command_status(ssm_command_id, client_ssm):
    response = client_ssm.get_command_invocation(
        CommandId=ssm_command_id
    )

    if response['Status'] is 'TimedOut' or response['Status'] is 'Success' or response['Status'] is 'Failed':
        return True
    else:
        return False

def lambda_handler(event, context):
    remaining_time = context.get_remaining_time_in_millis()

    # Retrieve the current region name
    client_session = boto3.session.Session()
    region = client_session.region_name

    # Payload to be passed on by the Cloudwatch rule
    _payload = '{ "Activation_Key": "eu_1b673cc3b4bc93137f5a3a2655d9df23", "Role_ARN": "arn:aws:iam::879633881541:role/swo_x_account_role", "Output_S3_Bucket": "swo-agent-logs", "Output_S3_Key_Prefix_Windows": "customer4/commvault/windows", "Output_S3_Key_Prefix_Linux": "customer4/commvault/linux", "Tag_Key": "swoMonitor", "Tag_Value": "1", "External_Id": "57a2d9d9-37f0-4435-aadf-1257142f2bcc", "SNS_Topic": "arn:aws:sns:ap-southeast-1:205041875266:lambda_notification" }'
    _payload = _payload.encode()

    client_lambda = boto3.client('lambda', region_name=region)
    client_ssm = boto3.client('ssm', region_name=region)

    res = client_lambda.invoke(
        FunctionName='x_account_site247_installer',
        InvocationType='RequestResponse',
        Payload=_payload,
        )
    
    streaming_body = res['Payload']
    retval = streaming_body.read().decode('utf-8')

    try:
        for region in retval.keys():
            region_data = retval[region]
            for instance_data in region_data:
                for instance in instance_data.keys():
                    ssm_command_id = instance_data[instance]
                    _count = 0
                    while not (check_ssm_command_status(ssm_command_id, client_ssm)):
                        time.sleep(10)
                        if _count < 12:
                            _count += 1
                        else:
                            logging.info('Couldn\'t verify the status of command id {0}'.format(ssm_command_id))
                            break
                    logging.info('Command ID {0} execution finished'.format(ssm_command_id))
    except:
        logger.info('Error in parsing command information')

    return remaining_time