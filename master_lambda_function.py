""" One function to rule them all"""

import boto3

def lambda_handler(event, context):
    remaining_time = context.get_remaining_time_in_millis()
    return remaining_time