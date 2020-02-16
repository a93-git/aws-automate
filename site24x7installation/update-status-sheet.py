""" Retrieve objects from S3 bucket (in the Customer's account) using Lambda 
function in the Master account which is triggered by the SNS topic in the 
customer's account which publishes message whenever there is a PutObject 
operation in the S3 bucket by the SSM command run by the Lambda function in the 
Master account triggered by the RunInstances operation in the customer's 
account 

// Environment Variables:
Role_ARN = ARN of the role to assume in customer's account
External_Id = External ID required for authentication
Status_Bucket = Bucket in which the status file is stored
Status_Object_Key = Object key of the status file

TODO IAM policy for the Lambda


// Run the following AWS CLI command to add a statement to the SNS access policy 
in the Customer's account

aws sns add-permission \
  --label <name for this policy statement> \
  --aws-account-id <maste account ID> \
  --topic-arn <SNS topic ARN> \
  --action-name Subscribe ListSubscriptionsByTopic Receive \
  --profile <profile name> \
  --region <region in which the SNS topic exists>

// Run the following AWS CLI commands to add the required resource based policy 
to the Lambda function in the Master account 

aws lambda add-permission \
  --function-name <name of Lambda function> \
  --source-arn <ARN of SNS topic in the customer account> \
  --statement-id <name for this policy statement> \
  --action "lambda:InvokeFunction" \
  --principal sns.amazonaws.com \
  --region <region code for Lambda function> \
  --profile <profile name>

// Run the following AWS CLI command to subscribe the Lambda function to the 
SNS topic
// Note that the following command needs to be run in the Master account (even 
though the SNS topic is in the Customer's account)
// Also the region _has_ to be the region in which the SNS topic exists in the
master account

aws sns subscribe \
  --protocol lambda \
  --topic-arn <ARN of SNS topic in the customer account> \
  --notification-endpoint <ARN of Lambda in the master account> \
  --region ap-south-1
"""
import boto3
import logging
import time
import json
import re
import os

logger = logging .getLogger()
logger.setLevel(logging.INFO)

role_arn = os.environ['Role_ARN']
external_id = os.environ['External_Id']
status_bucket = os.environ['Status_Bucket']
status_object_key = os.environ['Status_Object_Key']

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

def update_s3_object(bucket_name, object_key, message):
    """Update the file with current status of installation
    
    Arguments:
    bucket_name = Name of the bucket in which the status file is present
    object_key = Key of the status file
    message = message that needs to be appended

    Return:
    None
    """
    client_s3_status = boto3.client('s3')
    get_status_file = client_s3_status.get_object(Bucket=bucket_name, Key=object_key)
    if get_status_file['ResponseMetadata']['HTTPStatusCode'] == 200:
        streaming_body = get_status_file['Body']
        a = streaming_body.read().decode('utf-8')
        with open('test.txt', 'a+') as f:
            f.write(a)
            f.write(message)
    ret = client_s3_status.put_object(Bucket=bucket_name, Key=object_key)
    if ret['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info("Successfully updated the status file")
    else:
        logger.warning("Couldn't write the updated status file to S3 bucket")

def lambda_handler(event, context):
    """ Handle the event"""
    _time = time.time()

    creds = get_temp_creds(role_arn, external_id)

    if None in creds:
        logger.info("Cannot retrieve credentials")
        logger.warning("Creds provided: {0}".format(creds))
        exit()

    pat = re.compile(r'\bi-[0-9a-z]{17}\b')
    for record in event['Records']:
        status = 'failed'
        m = json.loads(record['Sns']['Message'])
        event_name = m['detail']['eventName']
        if 'PutObject' in event_name:
            bucket_name = m['detail']['requestParameters']['bucketName']
            object_key = m['detail']['requestParameters']['key']
            if 'stdout' in object_key.split('/')[-1]:
                instance_id = re.search(pat, object_key).group()
                client_s3 = boto3.client('s3', aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
                o = client_s3.get_object(Bucket=bucket_name, Key=object_key)
                if o['ResponseMetadata']['HTTPStatusCode'] == 200:
                    streaming_body = o['Body']
                    content = streaming_body.read().decode('utf-8')
                    if 'already running' in content or 'already installed' in content or 'started successfully' in content or 'completed' in content:
                        status = 'success'
                    else:
                        status = 'failure'
                    message = '{0}, {1}'.format(instance_id, status)
                    update_s3_object(status_bucket, status_object_key, message)
            else:
                logger.info('Skipping the stderr file')
                logger.info(event_name)
        else:
            logger.info('Event type is not valid')
            logger.info(event_name)

    logging.info("Total time of execution is {0}".format(time.time() - _time))