import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def lambda_handler(event, context):
	region = os.environ['Region']
	activation_key = os.environ['Activation_Key']
	script_url_windows = os.environ['Script_Url_Windows']
	package_url_windows = os.environ['Package_Url_Windows']
	script_url_linux = os.environ['Script_Url_Linux']
	package_url_linux = os.environ['Package_Url_Linux']
	tag_key = os.environ['Tag_Key']
	tag_value = os.environ['Tag_Value']
	document_version = '$LATEST'
	timeout_seconds = 120
	output_s3_bucket_name = os.environ['Output_S3_Bucket']
	service_role_arn = os.environ['Service_Role_Arn']
	notification_arn = os.environ['Notification_Arn']
	cw_log_group_name = os.environ['CW_Log_Group_Name']
	

	client_ssm = boto3.client('ssm', region_name=region)
	client_ec2 = boto3.client('ec2', region_name=region)

	# Get a list of all the EC2 instances with the given tag key and value
	ec2_data = client_ec2.describe_instances(
		Filters= [
			{
				'Name': "tag:{0}".format(tag_key),
				'Values': [tag_value]
			}
		]
	)


	def send_command(document_name, output_s3_key_prefix, command, instance_id):
		client_ssm.send_command(
			Targets=[
				{
					'Key': 'InstanceIds',
					'Values': [
						instance_id]
				}
			],
			DocumentName=document_name,
			DocumentVersion=document_version,
			TimeoutSeconds=timeout_seconds,
			Parameters={
				'commands': [command]
			},
			OutputS3BucketName=output_s3_bucket_name,
			OutputS3KeyPrefix=output_s3_key_prefix,
			ServiceRoleArn=service_role_arn,
			NotificationConfig={
				'NotificationArn': notification_arn,
				'NotificationEvents': ['Success', 'TimedOut', 'Failed'],
				'NotificationType': 'Invocation'
			},
			CloudWatchOutputConfig={
				'CloudWatchLogGroupName': cw_log_group_name,
				'CloudWatchOutputEnabled': True
		    }
	    )
	    
	ec2_matching = []
	
	for reservation in ec2_data['Reservations']:
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
			        output_s3_key_prefix = 'windows/cvAgent'
			        # No need to check if the service is already running because if it is, the script won't proceed with installation
			        command = "Invoke-WebRequest -Uri " + script_url_windows + " -OutFile C:/Windows.ps1 ; C:/windows.ps1 " + package_url_windows + " " + activation_key
			        instance_id = x[0]
			        send_command(document_name, output_s3_key_prefix, command, instance_id)
			else:
				logger.info("EC2 instance {0} is in {1} state".format(x[0], x[2]))
		elif x[1] == 'running':
			document_name = 'AWS-RunShellScript'
			output_s3_key_prefix = 'linux/cvAgent'
			command = r"echo 'starting installation of commvault agent'; a=$(cat /etc/os-release | grep 'NAME=\"Red Hat Enterprise Linux\"'); echo $a; b=$(cat /etc/os-release | grep -P 'VERSION=\"8\.[0-9]+'); echo $b; if [[ -z $a ]]; then echo 'Not RHEL'; curl -o /tmp/InstallCommvaultAgent.sh " + script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + package_url_linux + " " + activation_key + "; elif [[ -z $b ]]; then echo 'Not RHEL 8'; curl -o /tmp/InstallCommvaultAgent.sh " + script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + package_url_linux + " " + activation_key + "; else echo 'It is RHEL 8. Installing glibc, libnsl and libxcrypt'; yum install glibc libnsl libxcrypt -y; curl -o /tmp/InstallCommvaultAgent.sh " + script_url_linux + "; sh /tmp/InstallCommvaultAgent.sh " + package_url_linux + " " + activation_key + "; fi" 
			logger.info('Command is {0}'.format(command))
			instance_id = x[0]
			send_command(document_name, output_s3_key_prefix, command, instance_id)
		else:
			logger.info("EC2 instance {0} is in {1} state".format(x[0], x[1]))
