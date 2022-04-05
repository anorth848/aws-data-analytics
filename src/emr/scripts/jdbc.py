import logging
from util import get_secret
from pyspark.sql import SparkSession


def get_spark(secret_id, table_name, jdbc_config):
    jdbc_config = jdbc_config if jdbc_config is not None else {}
    secret = get_secret(secret_id)
    engine = secret['engine']
    host = secret['host']
    port = secret['port']
    dbname = secret['dbname']

    if engine.startswith('postgres'):
        driver = 'org.postgresql.Driver'
        engine = 'postgresql'
        logging.info('Engine is postgresql')
    else:
        raise ValueError(f'Engine {engine} not yet supported.')

    jdbc_config.update({
        'url': f'jdbc:{engine}://{host}:{port}/{dbname}?sslmode=require',
        'user': secret['username'],
        'password': secret['password'],
        'fetchSize': 10000,
        'driver': driver
    })

    # infer dbtable if the options are not explicitly specified
    if 'query'not in jdbc_config and 'dbtable' not in jdbc_config:
        jdbc_config['dbtable'] = table_name

    spark = SparkSession \
        .builder \
        .appName(f'{dbname}.{table_name}_to_HudiLake') \
        .getOrCreate()
    spark_jdbc = spark.read.format('jdbc') \
        .options(**jdbc_config)

    return spark, spark_jdbc, dbname
