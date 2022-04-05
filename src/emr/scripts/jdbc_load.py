import argparse
import json
import logging
import os
from datetime import datetime
from jdbc import get_spark

lake_location_uri = os.path.join(os.environ['BRONZE_LAKE_S3URI'], '')
log_level = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=log_level)


def get_args():
    parser = argparse.ArgumentParser()
    parser.add_argument('--table_name', default='public.customer')
    args = parser.parse_args()
    return args


def main():
    args = get_args()
    table_name = args.table_name
    f = open('/mnt/var/lib/instance-controller/public/runtime_configs/configs.json')
    config_dict = json.load(f)
    logging.debug(json.dumps(config_dict, indent=4))

    database_config = config_dict['DatabaseConfig']
    table_config = config_dict['StepConfigs'][table_name]
    secret_id = database_config['secret']
    spark_jdbc_config = table_config['spark_jdbc_config'] if 'spark_jdbc_config' in table_config else None

    spark, spark_jdbc, source_db = get_spark(secret_id, table_name, spark_jdbc_config)
    spark.sparkContext.setLogLevel(log_level)
    table_prefix = f"{source_db}/{table_name.replace('.','/')}"

    precombine_field = table_config['hudi_config']['watermark']

    if precombine_field == 'trx_seq':
        # Downstream we will merge CDC using AR_H_CHANGE_SEQ as the key if trx_seq is the precombine field
        # https://docs.aws.amazon.com/dms/latest/userguide/CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Expressions.html#CHAP_Tasks.CustomizingTasks.TableMapping.SelectionTransformation.Expressions-Headers
        # Generate this field for the full load
        trx_seq = datetime.now().strftime('%Y%m%d%H%M%S000000000000000000000')
    else:
        raise RuntimeError('Only trx_seq for precombine is currently supported')

    spark_jdbc.load().createOrReplaceTempView('temp_view')

    #  Hudi requires columns to be in the same order, data type, and null constraints
    df = spark.sql(f"""
        SELECT CASE WHEN 1=0 THEN NULL ELSE 'I' END AS Op,
        t.*,
        CASE WHEN 1=0 THEN NULL ELSE '{trx_seq}' END AS trx_seq,
        CASE WHEN 1=0 THEN NULL ELSE FALSE END AS _hoodie_is_deleted
        FROM temp_view t
    """)

    df.write \
        .format('parquet') \
        .mode('overwrite') \
        .save(os.path.join(lake_location_uri, 'full', table_prefix))


if __name__ == "__main__":
    main()
