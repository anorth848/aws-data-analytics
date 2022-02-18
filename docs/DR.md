# Disaster Recovery

## Summary

Disaster recovery involves creating this stack in another AWS account, and running the full suite of pipelines once the source RDBMS has been failed over.

## Assumptions

### RDS snapshot replication to DR region (Out of scope)

This Data Lake system relies on an RDS Database as the primary data source.   
It is crucial that the RDS Instance is [configured to replicate snapshots to the target region](https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_ReplicateBackups.html).
If we do not have the RDS Database, then this DR plan will not work.

## Implementation

### Installation 

Follow the installation instructions found in the main [README](../README.md) to install this solution in the DR AWS region.

### Failover   

Once a Disaster has been declared

- The RDS Database will need to be restored from snapshot in the target Region (Out of scope)
- In the DR Region
  - Ensure the AWS SecretsManager secret is correct for the restored RDS endpoint
  - Ensure the DMS Infrastructure has been created and the replication task is running
- Enable the jdbc_load Cloudwatch event schedule
  - Example: `aws events enable-rule --name <stack-name>-EmrPip-LaunchEmrPipelineLambdaR-V2WES6HWSB58`

Once these steps have been performed, the hudi tables will be recreated in the DR Region and continuous updates will be applied.