# aws-automate
Boto3 scripts to automate repetitive tasks in AWS

* Note these scripts need to be setup as Lambda functions (unless stated otherwise)

##

1. Tag EC2 instances
2. Install site24x7 monitoring agent on tagged VMs in all the regions
3. Get the list of running processes on an instance (Linux or Windows)
4. Take AMI backup of all the EC2 instances in the given AWS account and send the notification email
5. Scheduled stop/start of EC2 and RDS instances that match a given tag (need to set up a cron job)

## TODO
1. Fix the auto start/stop script for Lambda function
2. Add the IAM policies required for the site24x7 agent installation Lambda function
