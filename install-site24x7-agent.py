""" A script to install Site24x7 monitoring agent on the Windows and Linux EC2 instances (matching a given pair of Tag key and value) in AWS environment

** SSM agent needs to be installed on all the instances where we want to install the agent**

We need to set up the following environment variables in the Lambda:
Activation_Key - Unique customer key
Tag_Key - Tag key to look for
Tag_Value - Tag value for the corresponding Tag_Key
Output_S3_Bucket - S3 bucket to store the output of the SSM command
Output_S3_Key_Prefix_Windows - S3 bucket folder name inside the above bucket for Windows instances
Output_S3_Key_Prefix_Linux - S3 bucket folder name inside the above bucket for Windows instances
Service_Role_Arn - ARN of the role to allow the SNS topic in the SSM command to send the notification
Notification_Arn - ARN of the SNS topic that will send the notification (failure or success of the SSM command)
CW_Log_Group_Name - Cloudwatch log group name to save the output of the Lambda function
"""
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

class Site24x7Installer():
    activation_key = os.environ['Activation_Key']
    tag_key = os.environ['Tag_Key']
    tag_value = os.environ['Tag_Value']
    document_version = '$LATEST'
    timeout_seconds = 120
    output_s3_bucket_name = os.environ['Output_S3_Bucket']
    output_s3_key_prefix_linux = os.environ['Output_S3_Key_Prefix_Linux']
    output_s3_key_prefix_windows = os.environ['Output_S3_Key_Prefix_Windows']
    service_role_arn = os.environ['Service_Role_Arn']
    notification_arn = os.environ['Notification_Arn']
    cw_log_group_name = os.environ['CW_Log_Group_Name']

    def __init__(self, region):
        """ Instantiate the class, create ssm and ec2 clients and fetch the ec2 data for given tag keys and values
        """
        self.client_ssm = boto3.client('ssm', region_name=region)
        self.client_ec2 = boto3.client('ec2', region_name=region)

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
        self.client_ssm.send_command(
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
            ServiceRoleArn=self.service_role_arn,
            NotificationConfig={
                'NotificationArn': self.notification_arn,
                'NotificationEvents': ['Success', 'TimedOut', 'Failed'],
                'NotificationType': 'Invocation'
            },
            CloudWatchOutputConfig={
                'CloudWatchLogGroupName': self.cw_log_group_name,
                'CloudWatchOutputEnabled': True
            }
        )

    def check_ssm_status(self, instance_id):
        try:
            a = self.client_ssm.describe_instance_information(Filters=[{'Key':'InstanceIds', 'Values': [instance_id]}])['InstanceInformationList'][0]['PingStatus']
            logger.info("Ping status is {0}".format(a))
            return True
        except Exception as e:
            logger.info("SSM agent is not installed. Error message is {0}".format(e))
            return False

    def install_agent(self):
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
                        command = "If (Get-Service '" + service_name + "' ) { Restart-Service -Name '" + service_name + "' } Else { echo 'we are in the else block'; Start-Job -Name WebReq -ScriptBlock { Invoke-WebRequest -Uri " + url + " -OutFile " + output + " }; Wait-Job -Name WebReq; Test-Path " + output + " -PathType Leaf; msiexec.exe /i " + output + " EDITA1=" + self.activation_key + " ENABLESILENT=YES REBOOT=ReallySuppress /qn }"
                        instance_id = x[0]
                        if self.check_ssm_status(instance_id):
                            self.send_command(instance_id, command, document_name, self.output_s3_key_prefix_windows)
                        else:
                            logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
                else:
                    logger.info("EC2 instance {0} is in {1} state".format(x[0], x[2]))
            elif x[1] == 'running':
                document_name = 'AWS-RunShellScript'
                command = 'a=$(/etc/init.d/site24x7monagent status | head -1); if [[ $a == "Site24x7 monitoring agent service is up" ]]; then echo "Agent is already installed" > /var/log/test.log; /etc/init.d/site24x7monagent restart; else bash -c "$(curl -sL https://staticdownloads.site24x7.eu/server/Site24x7InstallScript.sh)" readlink -i -key=' + self.activation_key + ' ; fi'
                instance_id = x[0]
                if self.check_ssm_status(instance_id):
                    self.send_command(instance_id, command, document_name, self.output_s3_key_prefix_linux)
                else:
                    logger.info("Skipping instance id {0} as SSM agent is not installed".format(instance_id))
            else:
                logger.info("EC2 instance {0} is in {1} state".format(x[0], x[1]))

def lambda_handler(event, context):
    for region in REGIONS.values():
        a = Site24x7Installer(region)
        a.install_agent()