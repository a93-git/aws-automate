""" Creates and returns a temporary session token """

import boto3

class GetSession():
    """Get session data"""

    def __init__(self):
        """ Initialize object"""
        pass

    def get_session_data(self, external_id, role_arn, duration_seconds=900, role_session_name='default'):
        """ Get session data
        
        Arguments:
        external_id - ID to authenticate with another AWS account
        role_arn - Role ARN of the role (in the another AWS account) to assume
        duration_seconds - Duration of validity for the session data in seconds (minimum and default is 900)
        role_session_name - Name for the session ('default' is the default value)

        Returns:
        A tuple of AWSAccessKeyId, AWSSecretAccessKey and SessionToken
        """
        client_sts = boto3.client('sts')
        try:
            a = client_sts.assume_role(
                RoleSessionName=role_session_name, 
                RoleArn=role_arn, 
                DurationSeconds=duration_seconds, 
                ExternalId=external_id)
            return (a['Credentials']['AccessKeyId'], 
                a['Credentials']['SecretAccessKey'], 
                a['Credentials']['SessionToken'])
        except Exception as e:
            print("Error in retrieving temporary credentials")
            print(e)
            return(None, None, None)