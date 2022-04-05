import boto3
import json
import os
import backoff
from datetime import datetime
from boto3.dynamodb.conditions import Key
from aws_lambda_powertools import Logger

logger = Logger()

sfn_arn = os.environ.get('STEPFUNCTION_ARN')
config_table = os.environ.get('CONFIG_TABLE')
runtime_bucket = os.environ.get('RUNTIME_BUCKET')
bronze_lake_uri = os.environ['BRONZE_LAKE_S3URI']
silver_lake_uri = os.environ['SILVER_LAKE_S3URI']
sfn_client = boto3.client('stepfunctions')
topic_arn = os.environ.get('TOPIC_ARN')


def write_configs(execution_id, data):
    object_prefix = f'runtime/stepfunctions/{sfn_arn.split(":")[-1]}/{execution_id}/'
    s3 = boto3.resource('s3')
    s3.Object(runtime_bucket, os.path.join(object_prefix, "configs.json")).put(Body=data.encode('utf-8'))
    s3_uri = os.path.join('s3://', runtime_bucket, object_prefix)

    return s3_uri


def munge_configs(items, pipeline_type):
    configs = {
        'DatabaseConfig': {},
        'StepConfigs': {},
        'PipelineConfig': {},
    }
    # If the pipeline type is in specific system reserved words, assume it is a system pipeline
    if pipeline_type in ['jdbc_load', 'seed_hudi', 'continuous_hudi', 'incremental_hudi']:
        pipeline = f'pipeline::system::{pipeline_type}'
        step_prefix = 'step::system::'
        is_system = True
    # Otherwise, treat as a custom pipeline
    else:
        pipeline = f'pipeline::custom::{pipeline_type}'
        step_prefix = f'step::{pipeline_type}::'
        is_system = False

    for config in items:
        if config['config'] == 'database::config':
            configs['DatabaseConfig'] = config
        elif config['config'] == pipeline:
            configs['PipelineConfig'] = config
            configs['PipelineConfig']['emr_config']['step_parallelism'] = int(config['emr_config']['step_parallelism'])
            configs['PipelineConfig']['emr_config']['worker']['count'] = int(config['emr_config']['worker']['count'])
            if 'maximize_resource_allocation' not in config['emr_config']:
                configs['PipelineConfig']['emr_config']['maximize_resource_allocation'] = 'false'
            configs['PipelineConfig']['is_system'] = is_system
            logger.info(f'Pipeline type: {pipeline_type} Is System: {is_system}')
        elif config['config'].startswith(step_prefix):
            step_name = config['config'].split('::')[-1]
            configs['StepConfigs'][step_name] = config
            logger.info(f'Step {step_name} detected pipeline {pipeline_type}')
    return configs


def get_configs(identifier, pipeline_type):
    dynamodb = boto3.resource('dynamodb')
    table = dynamodb.Table(config_table)
    items = []
    response = table.query(
        KeyConditionExpression=Key('identifier').eq(identifier)
    )
    for item in response['Items']:
        items.append(item)

    while 'LastEvaluatedKey' in response:
        response = table.query(
            KeyConditionExpression=Key('identifier').eq(identifier),
            ExclusiveStartKey=response['LastEvaluatedKey']
        )
        for item in response['Items']:
            items.append(item)

    configs = munge_configs(items, pipeline_type)
    return configs


def get_hudi_configs(source_table_name, target_table_name, database_name, table_config, pipeline_type):
    primary_key = table_config['primary_key']
    precombine_field = table_config['watermark']
    glue_database = database_name

    hudi_conf = {
        'hoodie.table.name': target_table_name,
        'hoodie.datasource.write.recordkey.field': primary_key,
        'hoodie.datasource.write.precombine.field': precombine_field,
        'hoodie.datasource.hive_sync.database': glue_database,
        'hoodie.datasource.hive_sync.enable': 'true',
        'hoodie.datasource.hive_sync.table': target_table_name
    }

    if pipeline_type == 'seed_hudi':
        source_s3uri = os.path.join(bronze_lake_uri, 'full', source_table_name.replace('_', '/', 2), '')
        hudi_conf['hoodie.datasource.write.operation'] = 'bulk_insert'
        hudi_conf['hoodie.bulkinsert.sort.mode'] = 'PARTITION_SORT'
    elif pipeline_type in ['incremental_hudi', 'continuous_hudi']:
        source_s3uri = os.path.join(bronze_lake_uri, 'incremental', target_table_name.replace('_', '/', 2), '')
        hudi_conf['hoodie.datasource.write.operation'] = 'upsert'
    else:
        raise ValueError(f'Operation {pipeline_type} not yet supported.')

    hudi_conf['hoodie.deltastreamer.source.dfs.root'] = source_s3uri

    if table_config['is_partitioned'] is False:
        partition_extractor = 'org.apache.hudi.hive.NonPartitionedExtractor'
        key_generator = 'org.apache.hudi.keygen.NonpartitionedKeyGenerator'
    else:
        partition_extractor = table_config['partition_extractor_class']
        hudi_conf['hoodie.datasource.write.hive_style_partitioning'] = 'true'
        hudi_conf['hoodie.datasource.write.partitionpath.field'] = table_config['partition_path']
        hudi_conf['hoodie.datasource.hive_sync.partition_fields'] = table_config['partition_path']
        if len(primary_key.split(',')) > 1:
            key_generator = 'org.apache.hudi.keygen.ComplexKeyGenerator'
        else:
            key_generator = 'org.apache.hudi.keygen.SimpleKeyGenerator'

    hudi_conf['hoodie.datasource.write.keygenerator.class'] = key_generator

    if 'transformer_sql' in table_config:
        hudi_conf['hoodie.deltastreamer.transformer.sql'] = table_config['transformer_sql']

    hudi_conf['hoodie.datasource.hive_sync.partition_extractor_class'] = partition_extractor

    logger.debug(json.dumps(hudi_conf, indent=4))

    return hudi_conf


def generate_system_steps(configs, pipeline_type):
    steps = []
    for table in configs['StepConfigs'].keys():
        spark_submit_args = ['spark-submit']
        config = configs['StepConfigs'][table]
        logger.debug(json.dumps(config, indent=4))
        if 'enabled' in config and config['enabled'] is True:
            if pipeline_type == 'jdbc_load':
                if 'spark_conf' in config and 'jdbc_load' in config['spark_conf']:
                    for k, v in config['spark_conf']['jdbc_load'].items():
                        spark_submit_args.extend(['--conf', f'{k}={v}'])

                spark_submit_args.extend(
                    ['/mnt/var/lib/instance-controller/public/scripts/jdbc_load.py', '--table_name', table])
                entry = {
                    'step_name': table,
                    'jar_step_args': spark_submit_args
                }

            elif pipeline_type.endswith('_hudi'):
                target_db_name = configs['DatabaseConfig']['target_db_name']
                source_table_name = '_'.join(
                    [configs['DatabaseConfig']['target_table_prefix'], table.replace('.', '_')])

                # Add the ability to redirect to custom target table names
                if 'override_target_table_name' in config:
                    target_table_name = config['override_target_table_name']
                # Otherwise infer target table name from source
                else:
                    target_table_name = source_table_name

                if 'spark_conf' in config and pipeline_type in config['spark_conf']:
                    for k, v in config['spark_conf'][pipeline_type].items():
                        spark_submit_args.extend(['--conf', f'{k}={v}'])

                spark_submit_args.extend([
                    '--class', 'org.apache.hudi.utilities.deltastreamer.HoodieDeltaStreamer',
                    '/usr/lib/hudi/hudi-utilities-bundle.jar',
                    '--table-type', 'COPY_ON_WRITE',
                    '--source-class', 'org.apache.hudi.utilities.sources.ParquetDFSSource',
                    '--enable-hive-sync',
                    '--target-table', target_table_name,
                    '--target-base-path', os.path.join(silver_lake_uri, target_table_name, ''),
                    '--source-ordering-field', config['hudi_config']['watermark']
                ])

                if 'transformer_class' in config['hudi_config']:
                    spark_submit_args.extend(['--transformer-class', config['hudi_config']['transformer_class']])

                if pipeline_type == 'seed_hudi':
                    spark_submit_args.extend(['--op', 'BULK_INSERT'])

                hudi_configs = get_hudi_configs(source_table_name, target_table_name, target_db_name,
                                                config['hudi_config'], pipeline_type)
                for k, v in hudi_configs.items():
                    spark_submit_args.extend(['--hoodie-conf', f'{k}={v}'])

                if pipeline_type == 'continuous_hudi':
                    spark_submit_args.extend(['--continuous'])

                entry = {
                    'step_name': table,
                    'jar_step_args': spark_submit_args
                }
            steps.append(entry)
            logger.info(f'Table added to stepfunction input: {json.dumps(entry, indent=4)}')
        else:
            logger.info(f'Table {table} is disabled, skipping. To enable, set attribute "enabled": true')
            continue

    return steps


def generate_custom_steps(configs):
    steps = []
    for step in configs['StepConfigs'].keys():
        spark_submit_args = ['spark-submit']
        config = configs['StepConfigs'][step]
        logger.debug(json.dumps(config, indent=4))
        if 'enabled' in config and config['enabled'] is True:
            if 'spark_conf' in config:
                for k, v in config['spark_conf'].items():
                    spark_submit_args.extend(['--conf', f'{k}={v}'])

            script_args = config['entrypoint']
            spark_submit_args.extend(script_args)
            entry = {
                'step_name': step,
                'jar_step_args': spark_submit_args
            }
            steps.append(entry)
            logger.info(f'Step added to StepFunction input: {json.dumps(entry, indent=4)}')
        else:
            logger.info(f'Step {step} is disabled, skipping. To enable, set attribute "enabled": true')
            continue
    return steps


def generate_sfn_input(identifier, config_s3_uri, configs, pipeline_type, lambda_context):
    is_system = configs['PipelineConfig']['is_system']
    if is_system is True:
        steps = generate_system_steps(configs, pipeline_type)
    else:
        steps = generate_custom_steps(configs)

    if len(steps) == 0:
        raise RuntimeError(f'No steps have been generated based on {pipeline_type}. Ensure they are configured and enabled.')

    sfn_input = {
        'lambda': {
            'function_name': lambda_context.function_name,
            'identifier': identifier,
            'pipeline_type': pipeline_type,
            'runtime_configs': config_s3_uri,
            'steps': steps,
            'pipeline': configs['PipelineConfig'],
            'log_level': os.environ.get('LOG_LEVEL', 'INFO')
        }
    }
    return sfn_input


@backoff.on_exception(backoff.expo, exception=RuntimeError, max_time=60)
def check_concurrent(pipeline_type, allowed_concurrent=False):
    #  Define a map which allows launching pipelines that can run concurrently (that don't conflict with each other)
    paginator = sfn_client.get_paginator('list_executions')
    pages = paginator.paginate(
        stateMachineArn=sfn_arn,
        statusFilter='RUNNING'
    )
    for page in pages:
        raise_error = False
        for execution in page['executions']:
            exec_arn = execution['executionArn']
            if allowed_concurrent is not False and len(allowed_concurrent) > 0:
                # If the pipeline is in allowed_concurrent check to see if this pipeline is allowed to run at the same time
                response = sfn_client.describe_execution(executionArn=exec_arn)
                sfn_input = json.loads(response['input'])
                if sfn_input['lambda']['pipeline_type'] not in allowed_concurrent:
                    raise_error = True
            # If the pipeline is not in allowed_concurrent, raise exception
            else:
                raise_error = True
            if raise_error is True:
                raise RuntimeError(
                    f"Pipeline type {pipeline_type} cannot run due to in-progress pipeline {exec_arn}"
                )


def launch_sfn(execution_id, sfn_input):
    response = sfn_client.start_execution(
        stateMachineArn=sfn_arn,
        name=execution_id,
        input=json.dumps(sfn_input)
    )
    return response


def send_sns(subject, message):
    sns_client = boto3.client('sns')
    sns_client.publish(
        TopicArn=topic_arn,
        Subject=subject,
        Message=message
    )


@logger.inject_lambda_context
def handler(event, context=None):
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    identifier = event['Identifier']
    pipeline_type = event['PipelineType']
    try:
        config_dict = get_configs(identifier, pipeline_type)
        allowed_concurrent = config_dict['PipelineConfig']['allowed_concurrent'] if 'allowed_concurrent' in config_dict['PipelineConfig'] else False
        check_concurrent(pipeline_type, allowed_concurrent)

        execution_id = f'{identifier}-{pipeline_type}-{timestamp}'
        config_s3_uri = write_configs(execution_id, json.dumps(config_dict, indent=4))
        logger.info(f'Runtime config written to: {config_s3_uri}.')
        sfn_input = generate_sfn_input(identifier, config_s3_uri, config_dict, pipeline_type, context)
        response = launch_sfn(execution_id, sfn_input)

        return {
            "statusCode": response['ResponseMetadata']['HTTPStatusCode'],
            "headers": {
                "Content-Type": "application/json"
            },
            "body": json.dumps({
                "executionArn ": response['executionArn']
            })
        }
    except Exception as inst:
        subject = f'FAILURE | {identifier} | {pipeline_type} | Lambda Launch'
        message = f'Launch EMR Pipeline failed: {inst}'
        send_sns(subject, message)
        raise


if __name__ == '__main__':
    test_event={
        'Identifier': 'hammerdb'
    }

    handler(event=test_event)
