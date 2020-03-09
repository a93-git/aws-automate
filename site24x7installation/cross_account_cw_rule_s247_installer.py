""" 
**** WORKING VERSION !!! ****
A script to install Site24x7 monitoring agent on the Windows and Linux EC2 instances 
(matching a given pair of Tag key and value) in AWS environment

** Note that there is an additional tag key, value filter for maintenance window
** To set up the start of maintenance window we are using cloudwatch rules. No need to configure the end 
of MW because the script timesout in 5 minutes or less. Also the timeout for SSM command is set to 2 mins

** SSM agent needs to be installed on all the instances where we want to install the agent**

No need to set up any environment variables. All the required information for the invocation of this Lambda is provided by the 
CW rule 'Configure Input' option. The JSON format is as below:

{
	"MaintenanceWindowTagValue": "<tagVlue>",
	"MaintenanceWindowTagKey": "<tagKey>",
	"Activation_Key": "<activationKey>",
	"Role_ARN": "<roleArnInCustomerAccount",
	"Output_S3_Bucket": "<buckeName>",
	"Output_S3_Key_Prefix_Windows": "<folderPrefixForWindows>",
	"Output_S3_Key_Prefix_Linux": "<folderPrefixForLinux>",
	"Tag_Key": "<tagKey>",
	"Tag_Value": "<tagValue>",
	"External_Id": "<externalID>",
	"SNS_Topic": "<snsTopicARN>"
}

Note:
    ** Set the timeout in basic settings to 5 minutes
"""


import boto3
import os
import logging
import datetime
import time
import json

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

logger = logging.getLogger()
logger.setLevel(logging.INFO)

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


class Site24x7Installer():
    """ Installs Site24x7 agent on all the instances having matching tag keys 
    and values in all the enabled regions using the activation key provided
    """

    def __init__(self, region, creds, event):
        """ Instantiate the class, create ssm and ec2 clients and fetch the ec2 data for given tag keys and values

        Arguments:
        region - AWS region in which to look for the resources
        creds - A tuple containing the access key ID, secret access key and a secret token
        event - event data passed to the function
        
        Return:
        None
        """
        self._return_values = []
        self.region = region
        self.client_ssm = boto3.client('ssm', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
        self.client_ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
        self.client_s3 = boto3.client('s3', aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
        self.activation_key = event['Activation_Key']
        self.tag_key = event['Tag_Key']
        self.tag_value = event['Tag_Value']
        self.document_version = '$LATEST'
        self.timeout_seconds = 120
        self.output_s3_bucket_name = event['Output_S3_Bucket']
        self.output_s3_key_prefix_linux = event['Output_S3_Key_Prefix_Linux']
        self.output_s3_key_prefix_windows = event['Output_S3_Key_Prefix_Windows']
        self.maintenance_window = event['MaintenanceWindowTagKey']
        self.maintenance_window_val = event['MaintenanceWindowTagValue']

        # Get a list of all the EC2 instances with the given tag key and value
        self.ec2_data = self.client_ec2.describe_instances(
            Filters= [
                {
                    'Name': "tag:{0}".format(self.tag_key),
                    'Values': [self.tag_value]
                },
                {
                    'Name': "tag:{0}".format(self.maintenance_window),
                    'Values': [self.maintenance_window_val]
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
                OutputS3KeyPrefix=output_s3_key_prefix
            )
            
            return retval
            
        except Exception as e:
            logger.info("Error in installing Site24x7 agent on instance id {0} in region {1}".format(instance_id, self.region))
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
                        url='https://staticdownloads.site24x7.com/server/Site24x7WindowsAgent.msi'
                        output = "C:\\Windows\\Temp\\Site24x7WindowsAgent.msi"
                        service_name = "Site24x7 Windows Agent"
                        # No need to check if the service is already running because if it is, the script won't proceed with installation
                        command = "If (Get-Service '" + service_name + "' ) { Restart-Service -Name '" + service_name + "'; echo 'Site24x7 agent is already installed on this machine. Restarting the agent.' } Else { echo 'Starting agent download...'; Start-Job -Name WebReq -ScriptBlock { Invoke-WebRequest -Uri " + url + " -OutFile " + output + " }; Wait-Job -Name WebReq; Test-Path " + output + " -PathType Leaf; msiexec.exe /i " + output + " EDITA1=" + self.activation_key + " ENABLESILENT=YES REBOOT=ReallySuppress /qn }"
                        instance_id = x[0]
                        if self.check_ssm_status(instance_id):
                            retval = self.send_command(instance_id, command, document_name, self.output_s3_key_prefix_windows)
                            if retval:
                                message[self.region].append({instance_id: retval['Command']['CommandId']})
                                self._return_values.append(retval)
                            else:
                                message[self.region].append({instance_id: "Error in installing SSM agent"})
                        else:
                            logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
                            message[self.region].append({instance_id: "SSM agent not installed"})
                else:
                    logger.info("EC2 instance {0} is in {1} state".format(x[0], x[2]))
                    message[self.region].append({x[0]: "EC2 instance in {0} state".format(x[2])})
            elif x[1] == 'running':
                document_name = 'AWS-RunShellScript'
                command = 'a=$(/etc/init.d/site24x7monagent status | head -1); if [[ $a == "Site24x7 monitoring agent service is up" ]]; then echo "Agent is already installed" > /var/log/test.log; /etc/init.d/site24x7monagent restart; else bash -c "$(curl -sL https://staticdownloads.site24x7.eu/server/Site24x7InstallScript.sh)" readlink -i -key=' + self.activation_key + ' ; fi'
                instance_id = x[0]
                if self.check_ssm_status(instance_id):
                    retval = self.send_command(instance_id, command, document_name, self.output_s3_key_prefix_linux)
                    if retval:
                        message[self.region].append({instance_id: retval['Command']['CommandId']})
                        self._return_values.append(retval)
                    else:
                        message[self.region].append({instance_id: "Error in installing SSM agent"})
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
                a = Site24x7Installer(region, creds, event)
                a.install_agent()
            except Exception as e:
                logger.info("Error in installing Site24x7 agent in region {0}".format(region))
                logger.error(e)
                message[region] = "Error occured in installing Site24x7 agents in this region"

        except Exception as e:
            logger.info("Error in sending SNS notification to Lambda")
            logger.error(e)
    
    sns_arn = event['SNS_Topic']
    subject = "Site24x7 agent installation details on {0}".format(datetime.datetime.now().strftime(r"%Y-%m-%d"))
    message_id = send_notification(message, sns_arn, subject)
    logger.info("Message ID is {0}".format(message_id['MessageId']))

    return "Total execution time: {0} seconds".format(time.time() - _time)
    