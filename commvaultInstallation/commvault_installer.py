"""A script to install Commvault agent on the Windows and Linux EC2 instances (matching a given pair of Tag key and value) in AWS environment

** SSM agent needs to be installed on all the instances where we want to install the agent**

"""


import boto3
import os
import logging
import datetime
import time
import json

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

message = {}




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


class CommvaultInstaller():



    def __init__(self, region, creds, event):
        """ Instantiate the class, create ssm and ec2 clients and fetch the ec2 data for given tag keys and values

        Arguments:
        region - AWS region in which to look for the resources
        creds - A tuple containing the access key ID, secret access key and a secret token

        Return:
        None
        """
        self._return_values = []
        self.region = region
        self.client_ssm = boto3.client('ssm', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
        self.client_ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
        self.activation_key = event['Activation_Key']
        self.script_url_windows = event['Script_Url_Windows']
        self.package_url_windows = event['Package_Url_Windows']
        self.script_url_linux = event['Script_Url_Linux']
        self.package_url_linux = event['Package_Url_Linux']
        self.tag_key = event['Tag_Key']
        self.tag_value = event['Tag_Value']
        self.document_version = '$LATEST'
        self.timeout_seconds = 120
        self.output_s3_bucket_name = event['Output_S3_Bucket']
        self.output_s3_key_prefix_windows = event['Output_S3_Key_Prefix_Windows']
        self.output_s3_key_prefix_linux = event['Output_S3_Key_Prefix_Linux']

        # Get a list of all the EC2 instances with the given tag key and value
        self.ec2_data = self.client_ec2.describe_instances(
            Filters= [
                {
                    'Name': "tag:{0}".format(self.tag_key),
                    'Values': [self.tag_value]
                }
            ]
        )

    def send_command(self, document_name, output_s3_key_prefix, command, instance_id):
        """ Sends the ssm command to the target VM

        Arguments:
        document_name - Name of the SSM Document to run
        output_s3_key_prefix - prefix for S3 bucket
        command - command to send
        instance_id - Target instance ID

        Returns:
        dict (with SSM command output) 
        """
        try:
            retval = self.client_ssm.send_command(
                Targets=[
                    {
                        'Key': 'InstanceIds',
                        'Values': [
                            instance_id]
                    }
                ],
                DocumentName=document_name,
                DocumentVersion=self.document_version,
                TimeoutSeconds=self.timeout_seconds,
                Parameters={
                    'commands': [command]
                },
                OutputS3BucketName=self.output_s3_bucket_name,
                OutputS3KeyPrefix=output_s3_key_prefix,
            )
            return retval

        except Exception as e:
            logger.info("Error in installing Commvault agent on instance id {0} in region {1}".format(instance_id, self.region))
            logger.error(e)
            return False

    def check_ssm_status(self, instance_id):
        """ Checks the ping status of the given instance ID in Systems Manager

        Arguments:
        instance_id - Instance ID to look for

        Returns:
        True - Online
        False - Offline
        """
        try:
            a = self.client_ssm.describe_instance_information(Filters=[{'Key':'InstanceIds', 'Values': [instance_id]}])['InstanceInformationList'][0]['PingStatus']
            logger.info("Ping status is {0} for instance {1} in region {2}".format(a, instance_id, self.region))
            return True
        except Exception as e:
            logger.info("SSM agent is not installed on instance {0} in region {1}. Error message is {2}".format(instance_id, self.region, e))
            return False

    def install_agent(self):
        """ Pulls everything together and installs the agent on all the VMs that are online
        
        Arguments:
        None
        
        Returns:
        None
        """
        message[self.region] = []

        ec2_matching = []
        
        for reservation in self.ec2_data['Reservations']:
            for instance in reservation['Instances']:
                if 'Platform' in instance.keys():
                    ec2_matching.append((instance['InstanceId'], instance['Platform'], instance['State']['Name']))
                else:
                    ec2_matching.append((instance['InstanceId'], instance['State']['Name']))
        
        for x in ec2_matching:
            if len(x) == 3:
                if x[2] == 'running':
                    if x[1] == 'windows':
                        document_name = 'AWS-RunPowerShellScript'
                        output_s3_key_prefix = self.output_s3_key_prefix_windows
                        # No need to check if the service is already running because if it is, the script won't proceed with installation
                        command = "Invoke-WebRequest -Uri " + self.script_url_windows + " -OutFile C:/Windows.ps1 ; C:/windows.ps1 " + self.package_url_windows + " " + self.activation_key
                        instance_id = x[0]
                        if self.check_ssm_status(instance_id):
                            retval = self.send_command(document_name, output_s3_key_prefix, command, instance_id)
                            if retval:
                                message[self.region].append({instance_id: retval['Command']['CommandId']})
                                self._return_values.append(retval)
                            else:
                                message[self.region].append({instance_id: "Error in installing Commvault agent. SSM send command failed."})
                        else:
                            logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
                            message[self.region].append({instance_id: "SSM agent not installed"})
                else:
                    logger.info("EC2 instance {0} is in {1} state".format(x[0], x[2]))
                    message[self.region].append({x[0]: "EC2 instance in {0} state".format(x[2])})
            elif x[1] == 'running':
                document_name = 'AWS-RunShellScript'
                output_s3_key_prefix = self.output_s3_key_prefix_linux
                command = r"echo 'starting installation of commvault agent'; a=$(cat /etc/os-release | grep 'NAME=\"Red Hat Enterprise Linux\"'); echo $a; b=$(cat /etc/os-release | grep -P 'VERSION=\"8\.[0-9]+'); echo $b; if [[ -z $a ]]; then echo 'Not RHEL'; curl -o /tmp/InstallCommvaultAgent.sh " + self.script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + self.package_url_linux + " " + self.activation_key + "; elif [[ -z $b ]]; then echo 'Not RHEL 8'; curl -o /tmp/InstallCommvaultAgent.sh " + self.script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + self.package_url_linux + " " + self.activation_key + "; else echo 'It is RHEL 8. Installing glibc, libnsl and libxcrypt'; yum install glibc libnsl libxcrypt -y; curl -o /tmp/InstallCommvaultAgent.sh " + self.script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + self.package_url_linux + " " + self.activation_key + "; fi" 
                instance_id = x[0]
                if self.check_ssm_status(instance_id):
                    retval = self.send_command(document_name, output_s3_key_prefix, command, instance_id)
                    if retval:
                        message[self.region].append({instance_id: retval['Command']['CommandId']})
                        self._return_values.append(retval)
                    else:
                        message[self.region].append({instance_id: "Error in installing Commvault agent. SSM send command failed."})
                else:
                    logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
                    message[self.region].append({instance_id: "SSM agent not installed"})
            else:
                logger.info("EC2 instance {0} in region {1} is in {2} state".format(x[0], self.region, x[1]))
                message[self.region].append({x[0]: "EC2 instance in {0} state".format(x[1])})


def send_notification(message, sns_arn, subject):
    """ Send SNS notification"""
    
    client_session = boto3.session.Session()
    region = client_session.region_name
    
    client_sns = boto3.client('sns', region_name=region)
    
    message_id = client_sns.publish(
        TopicArn=sns_arn,
        Message= repr(message),
        Subject = subject
        )
        
    return message_id

def lambda_handler(event, context):
    _time = time.time()
    role_arn = event['Role_ARN']
    external_id = event['External_Id']

    creds = get_temp_creds(role_arn, external_id)

    if None in creds:
        logger.error("Security credentials couldn't be retrieved. Exiting...")
        exit()

    for region in REGIONS.values():
        try:
            try:
                a = CommvaultInstaller(region, creds, event)
                a.install_agent()
            except Exception as e:
                logger.info("Error in installing Commvault agent in region {0}".format(region))
                logger.error(e)
                message[region] = "Error occured in installing Commvault agents in this region"
        except Exception as e:
            logger.info("Error in Lambda execution")
            logger.error(e)

    sns_arn = event['SNS_Topic']
    subject = "Commvault agent installation details on {0}".format(datetime.datetime.now().strftime("%Y-%m-%d"))
    message_id = send_notification(message, sns_arn, subject)
    logger.info("Message ID is {0}".format(message_id['MessageId']))

    logger.info("Total execution time: {0} seconds".format(time.time() - _time))
    return message