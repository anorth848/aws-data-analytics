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


def get_configs(table_name):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(table_name)
    items = []
    response = table.scan()
    for item in response['Items']:
        if 'step_parallelism' in item:
            item['step_parallelism'] = int(item['step_parallelism'])
            item['worker']['count'] = int(item['worker']['count'])
        items.append(item)

    while 'LastEvaluatedKey' in response:
        response = table.scan(ExclusiveStartKey=response['LastEvaluatedKey'])
        for item in response['Items']:
            if 'step_parallelism' in item:
                item['step_parallelism'] = int(item['step_parallelism'])
                item['worker']['count'] = int(item['worker']['count'])
            items.append(item)

    return items


def main():
    args = get_args()
    items = get_configs(args.table_name)
    print(items)
    with open('runtime-configs.json', 'w') as f:
        f.write(json.dumps(items, indent=4))

if __name__ == '__main__':
    main()