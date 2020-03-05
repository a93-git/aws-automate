""" Function to retrieve a secret from secrets manager

The role for Lambda execution should have secretsmanager:GetSecretValue policy statement attached

{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "VisualEditor0",
            "Effect": "Allow",
            "Action": "secretsmanager:GetSecretValue",
            "Resource": "arn:aws:secretsmanager:<region>:<accountNumber>:secret:*"
        }
    ]
}

Store the secret as keypair value. If the structure of JSON is such that it 
can't be stored as keypair value, store it in plain text format
"""
import boto3

def lambda_handler(event, context):
    client_session = boto3.session.Session()
    region = client_session.region_name
    client_secretsmanager = boto3.client('secretsmanager', region_name=region)
    response = client_secretsmanager.get_secret_value(
        SecretId='<secretName>'
    )
    print(response['SecretString']) # We have stored the secrets as plaintext

