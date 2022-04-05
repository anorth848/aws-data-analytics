import json
import logging
import os
import boto3
from pyspark.sql import SparkSession


boto3.setup_default_session(region_name=os.environ.get('REGION', 'us-east-1'))
source_location_uri = os.path.join(os.environ['SILVER_LAKE_S3URI'], '')
target_location_uri = os.path.join(os.environ['GOLD_LAKE_S3URI'], '')
log_level = os.environ.get('LOG_LEVEL', 'INFO')

logging.basicConfig(
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    level=log_level)


def get_hudi_options(instant_time):
    hudi_options = {
        'hoodie.datasource.query.type': 'incremental',
        'hoodie.datasource.read.begin.instanttime': instant_time
    }
    return hudi_options

def main():
    f = open('/mnt/var/lib/instance-controller/public/runtime_configs/configs.json')
    config_dict = json.load(f)
    logging.info(json.dumps(config_dict, indent=4))

    database_config = config_dict['DatabaseConfig']
    db_name = database_config['target_db_name']
    print(database_config)

    spark = SparkSession \
        .builder \
        .appName(f'{db_name}_denormalize') \
        .getOrCreate()

    #  Check to see if the target denormalized table exists, if it does, grab the max hudi instant time from the previous load
    try:
        client = boto3.client('glue')
        client.get_table(DatabaseName=db_name, Name='analytics_order_line')
        spark.read.format('org.apache.hudi').load(os.path.join(target_location_uri, 'analytics_order_line', ''))\
            .createOrReplaceTempView('aol')
        instant_time = spark.sql('''
            SELECT date_format(MAX(ol_instant_time), 'yyyyMMddHHmmss') as instant_time FROM aol
            ''').collect()[0][0]
        logging.info(f'Table exists and records current as of {instant_time}')
        dn_table_exists = True

    #  There is no good way to catch botocore.errorfactory exceptions, so this...
    except Exception as e:
        if type(e).__name__ == 'EntityNotFoundException':
            dn_table_exists = False
            instant_time = None
            logging.warning('Table analytics_order_line does not exist')
        else:
            raise

    # Register tables as temporary views
    for table in ['hammerdb_public_orders','hammerdb_public_customer', 'hammerdb_public_district',
                   'hammerdb_public_warehouse', 'hammerdb_public_item', 'hammerdb_public_order_line']:

        # We are using snapshot reads for dimension tables and incremental for order_line (if possible)
        if dn_table_exists is True and table == 'hammerdb_public_order_line':
            hudi_options = {
                'hoodie.datasource.query.type': 'incremental',
                'hoodie.datasource.read.begin.instanttime': instant_time
            }
        else:
            hudi_options = {
                'hoodie.datasource.query.type': 'snapshot'
            }
        spark.read.format('org.apache.hudi').options(**hudi_options).load(os.path.join(source_location_uri, table, ''))\
            .createOrReplaceTempView(table)

    # Create the denormalized dataframe
    df = spark.sql('''
        SELECT
            concat(cast(c_id as string), '-', cast(w_id as string), '-', cast(d_id as string), '-', cast(o_id as string)) as aol_sk,
            concat(cast(c_id as string), '-', cast(w_id as string), '-', cast(d_id as string)) as c_sk,
            c_id,
            w_id,
            d_id,
            o_id, 
            ol_number,
            o_entry_d,
            date_format(o_entry_d, 'yyyy/MM/dd') as order_date,
            i_id,
            c_first || ' ' || c_middle || ' ' || c_last as full_name,
            c_zip,
            c_phone,
            c_credit,
            c_credit_lim,
            c_discount,
            c_balance,
            c_ytd_payment,
            c_payment_cnt,
            c_delivery_cnt,
            w_name whouse_name,
            d_name district_name,
            ol_delivery_d delivery_date,
            ol_quantity quantity,
            ol_amount amount,
            i_name item_name,
            i_price item_price,
            to_date(ol._hoodie_commit_time, 'yyyyMMddHHmmss') as ol_instant_time
        FROM hammerdb_public_orders
        JOIN hammerdb_public_customer
            ON  o_c_id = c_id
            AND o_d_id = c_d_id
            AND o_w_id = c_w_id
        JOIN hammerdb_public_district
            ON  c_d_id = d_id
            AND c_w_id = d_w_id
        JOIN hammerdb_public_warehouse
            ON  d_w_id = w_id
        JOIN hammerdb_public_order_line ol
            ON  o_id = ol_o_id 
            AND o_d_id = ol_d_id
            AND o_w_id = ol_w_id
        JOIN hammerdb_public_item
            ON  ol_i_id = i_id
        ORDER BY aol_sk, ol_number, ol_instant_time
    ''')

    # If we are doing a full load because the table doesn't exist, persist it.. we'll need it for aggregation step as well
    if dn_table_exists is False:
        df.persist()

    hudi_conf = {
        'hoodie.table.name': 'analytics_order_line',
        'hoodie.datasource.write.recordkey.field': 'aol_sk,ol_number',
        'hoodie.datasource.write.precombine.field': 'ol_instant_time',
        'hoodie.datasource.write.partitionpath.field': 'order_date',
        'hoodie.datasource.write.keygenerator.class': 'org.apache.hudi.keygen.ComplexKeyGenerator',
        'hoodie.datasource.hive_sync.database': db_name,
        'hoodie.datasource.hive_sync.enable': 'true',
        'hoodie.datasource.hive_sync.table': 'analytics_order_line',
        'hoodie.datasource.hive_sync.partition_extractor_class': 'org.apache.hudi.hive.SlashEncodedDayPartitionValueExtractor'
    }
    if dn_table_exists is False:
        hudi_conf['hoodie.datasource.write.operation'] = 'bulk_insert'
        hudi_conf['hoodie.bulkinsert.sort.mode'] = 'PARTITION_SORT'
        hudi_conf['hoodie.bulkinsert.shuffle.parallelism'] = '32'
        writer = df.write.format('org.apache.hudi').mode('overwrite')
    else:
        hudi_conf['hoodie.datasource.write.operation'] = 'upsert'
        hudi_conf['hoodie.upsert.shuffle.parallelism'] = '32'
        writer = df.write.format('org.apache.hudi').mode('append')

    writer.options(**hudi_conf)\
        .save(os.path.join(target_location_uri, 'analytics_order_line', ''))


if __name__ == '__main__':
    main()
