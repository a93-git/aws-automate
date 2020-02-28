""" One function to rule them all

No environment variables (as of now)

Set the timeout according to the normal time of execution of all the Lambda function

TODO Implement a state function - tracks the current state of execution of all the four Lambda functions
TODO If timeout occurs, call subsequent Lambda function with current state
"""

import boto3
import json

def lambda_handler(event, context):
    remaining_time = context.get_remaining_time_in_millis()

    # Retrieve the current region name
    client_session = boto3.session.Session()
    region = client_session.region_name

    # Payload to be passed on by the Cloudwatch rule
    _payload = '{ "Activation_Key": "eu_1b673cc3b4bc93137f5a3a2655d9df23", "Role_ARN": "arn:aws:iam::879633881541:role/swo_x_account_role", "Output_S3_Bucket": "swo-agent-logs", "Output_S3_Key_Prefix_Windows": "customer4/commvault/windows", "Output_S3_Key_Prefix_Linux": "customer4/commvault/linux", "Tag_Key": "swoMonitor", "Tag_Value": "1", "External_Id": "57a2d9d9-37f0-4435-aadf-1257142f2bcc", "SNS_Topic": "arn:aws:sns:ap-southeast-1:205041875266:lambda_notification" }'
    _payload = _payload.encode()

    client_lambda = boto3.client('lambda', region_name=region)

    res = client_lambda.invoke(
        FunctionName='x_account_site247_installer',
        InvocationType='RequestResponse',
        Payload=_payload,
        )
    
    streaming_body = res['Payload']
    retval = streaming_body.read().decode('utf-8')
    print("Response is: {0}".format(retval))
    return remaining_time