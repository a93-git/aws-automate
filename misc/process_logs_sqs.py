""" Retrieve objects from S3 bucket (in the Customer's account) using Lambda 
function in the Master account which is triggered by the SQS queue in the 
customer's account which pushes message whenever there is a PutObject 
operation in the S3 bucket by the SSM command run by the Lambda function in the 
Master account triggered by the RunInstances operation in the customer's 
account 

*******************
IMPORTANT NOTE
*******************
S3 BUCKETS, LAMBDAS, SQS, CLOUDWATCH RULES NEED TO BE IN THE SAME REGION IN BOTH
THE ACCOUNTS
*******************

// Environment Variables:
Role_ARN = ARN of the role to assume in customer's account
External_Id = External ID required for authentication
Status_Bucket = Bucket in which the status file is stored
Status_Object_Key = Object key of the status file

** Set the timeout to 2 mins in the Basic settings section

TODO IAM policy for the Lambda
TODO Regex for old instance id format

// Add the following policy to the SQS permissions
// Note the SNS topic and the S3 bucket need to be in the same region

{
  "Version": "2012-10-17",
  "Id": "<policyName>",
  "Statement": [
    {
      "Sid": "Sid1581937356422",
      "Effect": "Allow",
      "Principal": {
        "AWS": "arn:aws:iam:<master account ID>:root"
      },
      "Action": "SQS:*",
      "Resource": "<ARN of the SQS queue>"
    },
    {
      "Sid": "Stmt1581936608643",
      "Effect": "Allow",
      "Principal": {
        "AWS": "<Lambda ROLE ARN for the function in Master account>"
      },
      "Action": "sqs:*",
      "Resource": "ARN of the SQS queue"
    },
    {
      "Sid": "AWSEvents_rule-1_Id6250701342402",
      "Effect": "Allow",
      "Principal": {
        "Service": "events.amazonaws.com"
      },
      "Action": "sqs:SendMessage",
      "Resource": "<ARN of the SQS queue>",
      "Condition": {
        "ArnEquals": {
          "aws:SourceArn": "<ARN of the Cloudwatch Rule>"
        }
      }
    }
  ]
}

// Run the following AWS CLI commands to add the required resource based policy 
to the Lambda function in the Master account for the SQS

aws lambda add-permission \
  --function-name <name of Lambda function> \
  --source-arn <ARN of SQS queue in the customer account> \
  --statement-id <name for this policy statement> \
  --action "lambda:*" \
  --principal sqs.amazonaws.com \
  --region <region code for Lambda function> \
  --profile <profile name>

// Run the following AWS CLI command to create an event source mapping for the 
Lambda function from the SQS queue
// Note that the following command needs to be run in the Master account (even 
though the SQS queue is in the Customer's account)
// Also the region _has_ to be the region in which the SNS topic exists in the
Customer's account

aws lambda create-event-source-mapping \
    --event-source-arn "<ARN of the SQS queue in the customer's account>" \
    --function-name "<name of the lambda function name in master account>" \
    --region <region of the sqs>
    --profile <profile of master account>

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
        with open('/tmp/test.txt', 'w+') as f:
            f.write(a) # Write the old content back
            f.write('\n') # Insert a newline
            f.write(message) # Write the new content
    f = open('/tmp/test.txt', 'rb') # Open a file object in byte mode
    ret = client_s3_status.put_object(Bucket=bucket_name, Body=f, Key=object_key)
    if ret['ResponseMetadata']['HTTPStatusCode'] == 200:
        logger.info("Successfully updated the status file")
    else:
        logger.warning("Couldn't write the updated status file to S3 bucket")

def lambda_handler(event, context):
    """ Handle the event"""
    logger.info("Event is: {0}".format(event))
    _time = time.time()

    creds = get_temp_creds(role_arn, external_id)

    if None in creds:
        logger.info("Cannot retrieve credentials")
        logger.warning("Creds provided: {0}".format(creds))
        exit()

    pat = re.compile(r'\bi-[0-9a-z]{17}\b') # Regex for Instance id; TODO new regex for old instance id format
    for record in event['Records']:
        status = 'failed'
        m = json.loads(record['body'])
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