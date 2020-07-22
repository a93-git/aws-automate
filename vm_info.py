import json
import boto3
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def get_temp_creds(role_arn, external_id, region):
    pass

def get_instance_list(creds, region):
    pass

def send_ssm_command(instance, creds, region):
    pass

def send_sns_notification(sns_topic, subject, message):
    pass

def parse_s3_logs(lambda_payload):
    pass

def lambda_handler(event, context):
    # get creds
    role_arn = event['Role_ARN']
    external_id = event['External_Id']
    REGION_CODES = event['Region_Codes']

    message = {}

    for region in REGION_CODES:
        message[region] = {}
        creds = get_temp_creds(role_arn, external_id, region)

        if None in creds:
            logger.error("Couldn't retrieve credentials for region: {0}".format(region))

        instance_list = get_instance_list(creds, region)

        for instance in instance_list:
            retval = send_ssm_command(instance, creds, region)
            message[region][instance] = retval['CommandId'] # TODO: confirm the return value structure

    sns_topic = event['SNS_Topic']
    customer_name = event['Customer_Name']
    account_number = event['Account_Number']
    subject = "EC2 OS info for {0} - {1}".format(customer_name, account_number)

    send_sns_notification(sns_topic, subject, message)
        
    # Call a separate lambda function to parse the S3 bucket logs
    lambda_payload = {
        'Customer_Name': customer_name,
        'Account_Number': account_number,
        'Role_ARN': role_arn,
        'External_Id': external_id,
        'Command_Ids': json.loads(message)
    }

    parse_s3_logs(lambda_payload)