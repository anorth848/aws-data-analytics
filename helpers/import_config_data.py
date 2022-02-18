import boto3
import argparse
import json
import os
import logging

log_level = os.environ.get('LOG_LEVEL', logging.INFO)

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=log_level)

def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--table_name')
    args = parser.parse_args()
    return args


def write_configs(table_name, items):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    with table.batch_writer() as batch:
        for item in items:
            batch.put_item(Item=item)


def main():
    args = get_args()
    with open('runtime-configs.json') as f:
        items = json.load(f)
        write_configs(args.table_name, items)


if __name__ == '__main__':
    main()