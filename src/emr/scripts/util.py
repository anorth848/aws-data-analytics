import boto3
import logging
import json


def get_secret(secret):
    client = boto3.client('secretsmanager')
    logging.info(f'Retrieving secret {secret}')
    response = client.get_secret_value(SecretId=secret)
    logging.debug(f'Retrieved Secret ARN {response["ARN"]} VersionId {response["VersionId"]}')
    return json.loads(response['SecretString'])
