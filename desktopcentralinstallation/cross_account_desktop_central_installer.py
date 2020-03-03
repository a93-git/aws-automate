""" A script to install Desktop Central agent on the Windows and Linux EC2 
instances (matching a given pair of Tag key and value) in AWS environment

** SSM agent needs to be installed on all the instances where we want to install the agent**

Environment variables:

Role_ARN - Role ARN in the customer's account
External_ID - For added security
Output_S3_Bucket - S3 bucket to store the output of the SSM command
Output_S3_Key_Prefix_Linux - S3 bucket folder name inside the above bucket for Linux instances
Output_S3_Key_Prefix_Windows - S3 bucket folder name inside the above bucket for Windows instances
Tag_Key - Tag key to look for
Tag_Value - Tag value corresponding to the above tag key
SNS_Topic - SNS topic in the Master account to send notification to
Username - For desktop central console
Password - For desktop central console
Remote_Office_Id - Remote office id in which to place the VM
Script_URL_Linux - 
Script_URL_Windows - 



Single line script for Linux - 

username='admin'; password='admin'; remote_office_id=1804; process=$(ps -elf | grep -i /usr/bin/dcservice | grep -v grep | awk '{print $15}'); if [ -x /usr/local/desktopcentralagent ]; then if [ -z $process]; then echo 'Agent is installed but not in running mode'; echo 'Starting the agent'; /usr/bin/dcservice -t; else echo 'Agent is installed and in running mode'; fi; else echo \"Agent is not installed on the Virtual machine\"; OS_Architecture=$(hostnamectl | grep -i Architecture | awk '{print $2}'); OS_Release=$(cat /etc/os-release | grep -i ID_LIKE | cut -d '=' -f2); OS_Version=$(cat /etc/os-release | grep -i VERSION_ID | head -n 1 | cut -d '=' -f2 | sed 's/\"//g'); if [[ \"$OS_Release\" == \"debian\" ]]; then echo \"Installing Unzip Package on Debian OS\"; sudo apt-get install zip unzip wget -y; elif [[ \"$OS_Release\" != \"debian\" ]]; then echo \"Installing Unzip Package on Rhel OS\"; yum install -y unzip wget; else echo \"Platform is not Supported for OS - $OS_Release\"; fi; /usr/bin/wget --save-cookies /tmp/cookies.txt --keep-session-cookies --no-check-certificate --post-data "j_username=${username}&j_password=${password}" --delete-after "https://desktop-msp.westeurope.cloudapp.azure.com/j_security_check"; token=$(date +%s); /usr/bin/wget --load-cookies /tmp/cookies.txt --no-check-certificate "https://desktop-msp.westeurope.cloudapp.azure.com/branchOfficeConf.do?actionToCall=downloadAgentZip&branch_id=$remote_office_id&fileDownloadToken=$token" -O Agent.zip; rm -rf /tmp/cookies.txt; unzip Agent.zip; cd directsetup; unzip DCLinuxAgent.zip; sed -i 's/10.199.140.7/51.144.0.242/g' serverinfo.json; chmod +x DesktopCentral_LinuxAgent.bin; echo \"Installing Agent on Machine now ......\"; ./DesktopCentral_LinuxAgent.bin; echo \"Installation is completed now. Please check the process.\"; fi
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

class DesktopCentralInstaller():
    
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
        self.tag_key = event['Tag_Key']
        self.tag_value = event['Tag_Value']
        self.document_version = '$LATEST'
        self.timeout_seconds = 120
        self.output_s3_bucket_name = event['Output_S3_Bucket']
        self.output_s3_key_prefix_linux = event['Output_S3_Key_Prefix_Linux']
        self.output_s3_key_prefix_windows = event['Output_S3_Key_Prefix_Windows']
        self.username = event['Username']
        self.password = event['Password']
        self.remote_office_id = event['Remote_Office_Id']
        self.script_url_linux = event['Script_Url_Linux']
        self.script_url_windows = event['Script_Url_Windows']
        # Get a list of all the EC2 instances with the given tag key and value
        self.ec2_data = self.client_ec2.describe_instances(
            Filters= [
                {
                    'Name': "tag:{0}".format(self.tag_key),
                    'Values': [self.tag_value]
                }
            ]
        )

    def send_command(self, instance_id, command, document_name, output_s3_key_prefix):
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
            logger.info("Error in installing Desktop Central agent on instance id {0} in region {1}".format(instance_id, self.region))
            logger.error(e)
            return False

    def check_ssm_status(self, instance_id):
        try:
            a = self.client_ssm.describe_instance_information(Filters=[{'Key':'InstanceIds', 'Values': [instance_id]}])['InstanceInformationList'][0]['PingStatus']
            logger.info("Ping status is {0} for instance {1} in region {2}".format(a, instance_id, self.region))
            return True
        except Exception as e:
            logger.info("SSM agent is not installed on instance {0} in region {1}. Error message is {2}".format(instance_id, self.region, e))
            return False

    def install_agent(self):
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
                        command = "Invoke-WebRequest -Uri " + self.script_url_windows + " -OutFile C:/Windows.ps1; C:/windows.ps1 " + self.username + " " + self.password + " " + self.remote_office_id
                        instance_id = x[0]
                        if self.check_ssm_status(instance_id):
                            retval = self.send_command(instance_id, command, document_name, output_s3_key_prefix)
                            if retval:
                                message[self.region].append({instance_id: retval['Command']['CommandId']})
                                self._return_values.append(retval)
                            else:
                                message[self.region].append({instance_id: "Error in installing Desktop Central agent. SSM send command failed."})
                        else:
                            logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
                            message[self.region].append({instance_id: "SSM agent not installed"})
                else:
                    logger.info("EC2 instance {0} is in {1} state".format(x[0], x[2]))
                    message[self.region].append({x[0]: "EC2 instance in {0} state".format(x[2])})
            elif x[1] == 'running':
                document_name = 'AWS-RunShellScript'
                output_s3_key_prefix = self.output_s3_key_prefix_linux
                
                command = "curl -o /tmp/dc_agent.sh " + self.script_url_linux + "; sudo sed -i 's/\r//' /tmp/dc_agent.sh; chmod +x /tmp/dc_agent.sh; /bin/bash /tmp/dc_agent.sh " + self.username + " " + self.password + " " + self.remote_office_id
                print("Command is {0}".format(command))
                instance_id = x[0]
                if self.check_ssm_status(instance_id):
                    retval = self.send_command(instance_id, command, document_name, output_s3_key_prefix)
                    if retval:
                        message[self.region].append({instance_id: retval['Command']['CommandId']})
                        self._return_values.append(retval)
                    else:
                        message[self.region].append({instance_id: "Error in installing Desktop Central agent"})
                else:
                    logger.info("Skipping instance id {0} in region {1} as SSM agent is not installed".format(instance_id, self.region))
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
                a = DesktopCentralInstaller(region, creds, event)
                a.install_agent()
            except Exception as e:
                logger.info("Error in installing Desktop Central agent in region {0}".format(region))
                logger.error(e)
                message[region] = "Error occured in installing Desktop Central agents in this region"
        except Exception as e:
            logger.info("Error in Lambda execution")
            logger.error(e)

    sns_arn = event['SNS_Topic']
    subject = "Desktop central agent installation details on {0}".format(datetime.datetime.now().strftime("%Y-%m-%d"))
    message_id = send_notification(message, sns_arn, subject)
    logger.info("Message ID is {0}".format(message_id['MessageId']))

    logger.info("Total execution time: {0} seconds".format(time.time() - _time))
    return message