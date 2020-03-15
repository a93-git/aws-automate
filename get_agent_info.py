import boto3
import logging
import os 

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

output_s3_key_prefix_linux = os.environ['Output_S3_Key_Prefix_Linux']
output_s3_key_prefix_windows = os.environ['Output_S3_Key_Prefix_Windows']
document_version = '$LATEST'
output_s3_bucket_name = os.environ['Output_S3_Bucket_Name']
timeout_seconds = 120

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

def get_vms_with_tags(region, creds, NextToken):
    client_ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
    
    if not NextToken:
        NextToken = ''

    res = client_ec2.describe_instances(
        Filters=[
            {
                'Name': 'tag-key',
                'Values': [
                    'swoBackup',
                    'swoMonitor',
                    'swoAntiMalware',
                    'swoPatch'
                    ]
            }
        ],
        NextToken=NextToken
    )
    
    return res

def check_ssm_status(client_ssm, vm_list):
    _ssm_status_result = client_ssm.describe_instance_information(
        Filters=[
            {
                'Key':'InstanceIds', 
                'Values': vm_list
            }
        ]
    )

    # Check what happens if a VM doesn't have SSM agent installed
    _ssm_status_result = [x['InstanceId'] for x in _ssm_status_result['InstanceInformationList'] if x['PingStatus'] == 'Online']

    return _ssm_status_result

def send_command(client_ssm, vm_list, command, document_name, output_s3_key_prefix):
    try:
        retval = client_ssm.send_command(
            Targets=[
                {
                    'Key': 'InstanceIds',
                    'Values': vm_list
                }
            ],
            DocumentName=document_name,
            DocumentVersion=document_version,
            TimeoutSeconds=timeout_seconds,
            Parameters={
                'commands': [command],
                'executionTimeout': ['720']
            },
            OutputS3BucketName=output_s3_bucket_name,
            OutputS3KeyPrefix=output_s3_key_prefix,
        )
        logger.debug('Return value from SSM send command is {0}'.format(retval))
        return retval

    except Exception as e:
        logger.error("Error in sending commands to the VMs {0}".format(vm_list))
        logger.error(e)
        return [None]


def lambda_handler(event, context):
    role_arn = os.environ['Role_Arn']
    external_id = os.environ['External_Id']
    
    creds = get_temp_creds(role_arn, external_id)
    
    if None not in creds:
        for region in REGIONS.values():
            retval = get_vms_with_tags(region, creds, None)
            ec2_matching = []
            if 'NextToken' in retval.keys() and retval['NextToken'] != '' and retval['NextToken'] is not None:
                while 'NextToken' in retval.keys():
                    for reservation in retval['Reservations']:
                        for instance in reservation['Instances']:
                            if 'Platform' in instance.keys():
                                ec2_matching.append((instance['InstanceId'], instance['Platform'], instance['State']['Name']))
                            else:
                                ec2_matching.append((instance['InstanceId'], instance['State']['Name']))
                    retval = get_vms_with_tags(region, creds, retval['NextToken'])
            else:
                for reservation in retval['Reservations']:
                    for instance in reservation['Instances']:
                        if 'Platform' in instance.keys():
                            ec2_matching.append((instance['InstanceId'], instance['Platform'], instance['State']['Name']))
                        else:
                            ec2_matching.append((instance['InstanceId'], instance['State']['Name']))
            
            while len(ec2_matching) != 0:
                _count = 50
                if len(ec2_matching) < _count:
                    _count = len(ec2_matching)
                
                _batch_to_process, ec2_matching = ec2_matching[:_count], ec2_matching[_count:]
                
                # Segregate Linux and Windows VMs
                _batch_linux_vms = [x for x in _batch_to_process if len(x) == 2]
                _batch_windows_vms = [x for x in _batch_to_process if len(x) == 3]
                
                client_ssm = boto3.client('ssm', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])

                if len(_batch_linux_vms) != 0:
                    _batch_linux_instance_ids = [x[0] for x in _batch_linux_vms if x[1] == 'running'] # Filter running instances
                    _batch_linux_instances_ssm_online = check_ssm_status(client_ssm, _batch_linux_vms) # Filter instances where the SSM status is online
                    logger.info('SSM agents installed on the following Linux VMs:')
                    logger.info(_batch_linux_instances_ssm_online)
                    document_name = 'AWS-RunShellScript'
                    output_s3_key_prefix = output_s3_key_prefix_linux
                    command = 'ls' #check agent status
                    _linux_retval = send_command(client_ssm, _batch_linux_instances_ssm_online, command, document_name, output_s3_key_prefix)

                if len(_batch_windows_vms) != 0:
                    _batch_windows_instance_ids = [x[0] for x in _batch_windows_vms if x[2] == 'running' ] # Filter running instances
                    _batch_windows_instances_ssm_online = check_ssm_status(client_ssm, _batch_windows_vms) # Filter instances where SSM status is online
                    logger.info('SSM agents installed on the following windows VMs:')
                    logger.info(_batch_windows_instances_ssm_online)
                    document_name = 'AWS-RunPowerShellScript'
                    output_s3_key_prefix = output_s3_key_prefix_windows
                    command = 'ls' #check agent status
                    # _windows_retval = send_command(client_ssm, _batch_windows_instances_ssm_online, command, document_name, output_s3_key_prefix)
                    

    else:
        logger.error('Couldn\'t retrieve credentials. Exiting')
        return False