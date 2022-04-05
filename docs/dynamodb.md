## Runtime Config table

The runtime config table contains items with configuration data related to:   
- Spark JDBC datasources and related configs
- EMR Pipelines and related configs
- Tables and related configs

### Partition Key/Sort Key

The PK/SK are:

```
identifier ( STRING, Partition key )
config  (STRING, Sort key)
```

- *identifier*: This attribute is meant to uniquely identify a group of config records related to a set of pipelines.   
  - ***This must match UseCase from the Parent stacks for the first configured pipeline***   
  - Additional pipelines can be arbitrarily named
- *config*: This attribute must be one of [database::config, pipeline::[system|custom]::<pipeline name>, step::[system|<pipeline name>]::<table name>].

#### Item specifics

In order for the system to function, each `identifier` group of items must have at least 3 `system` items for the `system` pipline to function.
Using `rdbms_analytics` as our identifier(UseCase), here is an example of the minimum number of items in DynamoDB if you just wanted to load the customer table:   

|identifier|config|
|----------|------|
|rdbms_analytics|database::config|
|rdbms_analytics|pipeline::system::jdbc_load|
|rdbms_analytics|step::system:public.customer|

##### Item schema

Each config entry type has its own expected schema

##### database::config

Currently only one jdbc datasource can be configured per pipeline. To add more jdbc data sources, you would configure a new identifier and group of pipelines/tables.

```
{
    "config": "database::config",
    "identifier": "rdbms_analytics",
    "secret": "secrets/manager/secret/name",    // This is the path to the connection information in AWS Secrets Manager
    "target_db_name": "use_case",               // This is the target glue database name 
    "target_table_prefix": "hammberdb"          // This is the prefix all glue tables will be created with EG: public.customer becomes hammerdb_public_customer

}
```

#### Pipelines 

Pipeline items have `config` attribute that starts with  `pipeline::`.   
Full `config` attribute format is `pipeline::<type>::<pipeline name>`.

##### System (`pipeline::sytem::`)

This system is built on Hudi tables. The initial creation and incremental processing of Hudi tables are considered `system` pipelines.   
System pipelines can be one of `[jdbc_load|seed_hudi|incremental_hudi|continuous_hudi]`   
**NOTE** The above system pipeline names should be considered reserved words and not used as custom pipeline names

##### Custom (`pipeline::custom::`)

Custom pipelines are use-case specific pipelines that can be added as post-steps to system pipelines.  
For example, a denormalization step for reporting purposes. 

##### Item format

`pipeline::` items are meant to tell the system how to launch the EMR cluster. (EG: Number of nodes, node type, parallelism, etc)

```
{
    "config": "pipeline::[system|custom]::[<name>]", // Type and name of the pipeline
    "identifier": "<UseCase>",
    "allowed_concurrent": ["<pipeline name>"],  // A list of pipelines that can safely run concurrently with this pipeline
    "emr_config": {                             // These configs get passed into the StepFunction and are used when creating the EMR cluster
                                                // At present, cluster instance options are limited, need to add Spot and Autoscaling support
        "release_label": "emr-6.5.0",
        "master": {
            "instance_type": "m5.xlarge"
        },
        "worker": {
            "count": "6",
            "instance_type": "r5.2xlarge"
        },
        "maximize_resource_allocation": "[true|false]", // Whether or not to set the EMR-specific "maximizeResourceAllocation" 

        "step_parallelism": 4                   // NOTE: Make sure your worker settings can handle the parallelism you choose
                                                //       This is especially important for continuous_load
    },
    "next_pipeline": {                          // When this pipeline completes, whether or not to launch the next pipeline
        "pipeline_type": "seed_hudi",           // Must be one of [ seed_hudi|incremental_hudi|continuous_hudi ]
        "enabled": true                         // set to false to disable launching the next pipeline
    },
}
```

#### step::[system|<custom name>::<step name>>

`step::` items indicate the steps that will be added to the cluster. 
This include Spark JDBC Options, EMR Job Step options, and Hudi options.

The item schema is different for system vs custom steps

##### System steps

A `step::system::<table_name>` item is shared by all system pipelines related to a specific hudi table.
The expected attributes are as follows:

```
{
    "config": "step::system::<table_name>",       // One item per table
    "identifier": "<UseCase>",
    "enabled": [true|false],                      // Enable or Disable the table 
    "hudi_config": {
        "primary_key": "<c,s,v>",               // Comma-separated list of primary key columns on the table       
        "watermark": "trx_seq",                 // The "tie-breaker" column, used as the precombine field for merging rows in Hudi
                                                // Currently only trx_seq (AR_H_CHANGE_SEQ from AWS DMS) is supported
                                                // https://aws.amazon.com/blogs/database/capture-key-source-table-headers-data-using-aws-dms-and-use-it-for-amazon-s3-data-lake-operations/
        "is_partitioned": [true|false],         // Whether or not to partition the Hudi table
        "partition_path": "<column>",           // Required only if is_partitioned is true, the column to partition on
        "partition_extractor_class": "<cls>"    // The Hive partition extractor class EG: org.apache.hudi.hive.MultiPartKeysValueExtractor
        "transformer_class": "<cls"             // [OPTIONAL] The DeltaStreamer partition class EG: org.apache.hudi.utilities.transform.SqlQueryBasedTransformer
        "transformer_sql": "<SQL STATEMENT AS s>// [OPTIONAL] The sql statement (must be set if transformer_class is SqlQueryBasedTransformer
    },
    "spark_jdbc_config": {                      // [OPTIONAL] this stanza is only used by jdbc_load pipeline and is passed directly to spark jdbc. 
                                                // Any option found here can be set: https://spark.apache.org/docs/latest/sql-data-sources-jdbc.html
        "<option>": "<value>"
    },
    "spark_conf": {                             // [OPTIONAL] this stanza is used to pass spark configurations to the emr job step
                                                // Any option found here can be set:  https://spark.apache.org/docs/latest/configuration.html#available-properties
        "<pipeline_type>": {                    // <pipeline type> must be one of: [ jdbc_load|seed_hudi|incremental_hudi|continuous_hudi ]
            "<option>": "<value"
        }
    }
}
```

Example record for public.order_line in rdbms_analytics grouping:    

```
{
    "config": "table::public.order_line",
    "identifier": "rdbms_analytics",
    "enabled": true,
    "hudi_config": {
        "primary_key": "ol_w_id,ol_d_id,ol_o_id,ol_number",
        "watermark": "trx_seq",
        "is_partitioned": true,
        "partition_path": "ol_w_id",
        "partition_extractor_class": "org.apache.hudi.hive.MultiPartKeysValueExtractor"
    },
    "spark_jdbc_config": {
        "dbtable": "public.order_line",
        "partitionColumn": "ol_w_id",
        "lowerBound": "0",
        "upperBound": "300",
        "numPartitions": "30"
    },
    "spark_conf": {
        "jdbc_load": {
            "spark.executor.cores": "2",
            "spark.executor.memory": "8g",
            "spark.executor.heartbeatInterval": "120s",
            "spark.network.timeout": "1200s",
            "spark.dynamicAllocation.enabled": "false",
            "spark.executor.instances": "12"
        },
        "seed_hudi": {
            "spark.executor.cores": "2",
            "spark.executor.memory": "8g",
            "spark.executor.heartbeatInterval": "90s",
            "spark.network.timeout": "900s",
            "spark.dynamicAllocation.enabled": "false",
            "spark.executor.instances": "12"
        },
        "incremental_hudi": {
            "spark.executor.cores": "2",
            "spark.executor.memory": "6g",
            "spark.executor.heartbeatInterval": "30s",
            "spark.network.timeout": "600s",
            "spark.dynamicAllocation.minExecutors": "2",
            "spark.dynamicAllocation.maxExecutors": "12"
        },
        "continuous_hudi": {
            "spark.executor.cores": "1",
            "spark.executor.memory": "4g",
            "spark.executor.heartbeatInterval": "30s",
            "spark.network.timeout": "300s",
            "spark.dynamicAllocation.minExecutors": "2",
            "spark.dynamicAllocation.maxExecutors": "6"
        }
    }
}
```

##### Custom steps

`step::<pipline name>::<step name>` are custom EMR scripts that can be added to custom pipelines.     
The anatomy of a custom step item is as follows:

```
{
    "config": "step::<pipeline name>::<step name>", //  One item per step
    "identifier": "<UseCase>",
    "enabled": [true|false],                        //  Enable or Disable the step 
    "spark_conf": {                                 //  [OPTIONAL] this stanza is used to pass spark configurations to the emr job step
                                                    //  Any option found here can be set:  https://spark.apache.org/docs/latest/configuration.html#available-properties
        "<option>": "<value"
    },
    "entrypoint": [
        "<script path>", "<parameter1>"             //  The path to the script and optional arguments to pass in 
    ]
}
```