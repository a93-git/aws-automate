""" List all the available EC2 resources in the current account"""

import boto3
import json
import getsession

REGION_NAMES = ['Ohio', 'N. Virginia', 'N. California', 'Oregon', 'Mumbai', 'Osaka-Local', 'Seoul', 'Singapore', 'Sydney', 'Tokyo', 'Canada', 'Frankfurt', 'Ireland', 'London', 'Paris', 'Stockholm', 'Sao Paulo']
REGION_CODES = ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'ap-south-1', 'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2', 'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-west-3', 'eu-north-1', 'sa-east-1']
REGIONS = dict(zip(REGION_NAMES, REGION_CODES))

class EC2Info():
    """Create an object to get EC2 data"""

    def __init__(self, external_id, role_arn, duration_seconds=900, role_session_name='default'):
        """ Create the client and initialize the object """
        self.instance_info = {}
        self.external_id = external_id
        self.role_arn = role_arn
        self.duration_seconds = duration_seconds
        self.role_session_name = role_session_name

    def get_access_token(self):
        creds = getsession.GetSession().get_session_data(
            self.external_id, 
            self.role_arn,
            duration_seconds=self.duration_seconds,
            role_session_name=self.role_session_name)
        if 'None' in creds:
            return None
        else:
            return creds

    def get_data(self, client_ec2, region):
        """ Retrieve the information about the EC2 instances in a given region

        Arguments:
        client_ec2 - boto3 client to AWS ec2 service for the given region

        Returns:
        A json object with the information about the instances

        Return structure:
        {
            Region: {
                'Instances': {
                    'InstanceId': {
                        'Platform': '',
                        'PublicIpAddress': '',
                        'PrivateIpAddress': '',
                        'InstanceType': '',
                        'InstanceState': ''
                    },
                    ...
                }
            }
        }
        """

        retval = {'Instances': {}}
        ec2_list = client_ec2.describe_instances()
        # self.instance_info[region] = {}
        for reservation in ec2_list['Reservations']:
            for instance in reservation['Instances']:
                retval['Instances'][instance['InstanceId']] = {}
                if 'Platform' in instance.keys():
                    retval['Instances'][instance['InstanceId']]['Platform'] = instance['Platform']
                else:
                    retval['Instances'][instance['InstanceId']]['Platform'] = "None"
                if 'PublicIpAddress' in instance.keys():
                    retval['Instances'][instance['InstanceId']]['PublicIpAddress'] = instance['PublicIpAddress']
                else:
                    retval['Instances'][instance['InstanceId']]['PublicIpAddress'] = "None"
                retval['Instances'][instance['InstanceId']]['InstanceState'] = instance['State']['Name']
                retval['Instances'][instance['InstanceId']]['InstanceType'] = instance['InstanceType']
                retval['Instances'][instance['InstanceId']]['PrivateIpAddress'] = instance['PrivateIpAddress']
        return retval

    def get_ec2_info(self):
        """ Loop over all the available regions and get the EC2 info
        
        Arguments:
        None
        
        Return:
        A json object of the regions, instances and their values
        
        Return Structure:
        
        {
            'Region1': {
                'Instances': {
                    'InstanceId': {
                        'Platform': '',
                        'PublicIpAddress': '',
                        'PrivateIpAddress': '',
                        'InstanceType': '',
                        'InstanceState': ''
                    },
                    ...
                },
                ...
            }
        }
        
        """

        creds = self.get_access_token()
        for region in REGIONS.values():
            self.instance_info[region] = {}
            try:
                client_ec2 = boto3.client('ec2', region_name=region, aws_access_key_id=creds[0], aws_secret_access_key=creds[1], aws_session_token=creds[2])
                retval = self.get_data(client_ec2, region)
                self.instance_info[region] = retval
            except boto3.exceptions.botocore.client.ClientError as e:
                print(e)
            except:
                raise

        return json.dumps(self.instance_info, indent=4)

# if __name__ == '__main__':
#     ec2_obj = EC2Info()
#     retval = ec2_obj.get_ec2_info()

#     with open('testec2info.json', 'w') as f:
#         f.write(retval)