"""


- Get the list of all the EC2 instances with applicable tags
- Filter the list with VMs that has SSM agent installed
- Send the agent checking command
- Check the output of the command
- If agent is running, set its value to 1 else 0
- Write the content to a file
- Upload the file to a s3 bucket

"""

import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# A dictionary of AWS regions and their corresponding region codes
REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

# A dictionary of Agent names and their corresponding commands to check the status
AGENT_NAMES = ['Site24x7', 'Trend', 'Commvault', 'DesktopCentral']
AGENT_COMMANDS = [('/opt/site24x7/monagent status', 'Get-Service "Site24x7 Monitoring Agent"'), ('service ds_agent status', 'Get-Service "ds_agent"'), ]
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

def get_secret(event):
    pass

def get_matching_ec2(tag, region, creds):
    pass

def get_ssm_status(ec2_list, region, creds):
    pass

def lambda_handler(event, context):

    # Retrieve the data required for this Lambda's execution from the secret manager
    lambda_data = get_secret(event)
    role_arn, external_id, tag_list = lambda_data[0], lambda_data[1], lambda_data[2]

    # Retrieve credentials to work in the 3rd party account
    creds = get_temp_creds(role_arn, external_id)

    if None in creds:
        logger.error("Error in getting credentials. Exiting")
        return False

    for region in REGIONS.keys():
        instance_value = {}
        for tag in tag_list:
            ec2_list = get_matching_ec2(tag, region, creds)
            ec2_ssm_online = get_ssm_status(ec2_list, region, creds)
            for agent in AGENTS:
                command_id = send_ssm_command(ec2_ssm_online, region, creds, s3_bucket, bucket_prefix)
                for i in command_id:
                    check_ssm_command_status(i, region, creds)
                for i in command_id:
                    command_output = check_command_output(i, region, creds)
                for i in zip(ec2_ssm_online, command_output):
                    if i[1] == 'Running':
                        instance_value[i[0]] = []
                        instance_value[i[0]].append(1)
                    else:
                        instance_value[i[0]] = []
                        instance_value[i[0]].append(0)
        with open('/tmp/instance_value.csv', 'w') as f:
            for i in instance_value.keys():
                f.write(instance_value[i])
                f.write('\n')
    write_to_s3(bucket_name, bucket_prefix, file_path, content)

    return True