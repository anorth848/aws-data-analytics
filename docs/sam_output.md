
```
$ sam build
Building codeuri: aws-data-analytics/src/lambdas/launch_emr_pipeline runtime: python3.9 metadata: {} architecture: x86_64 functions: ['EmrPipelineStack/LaunchEmrPipelineLambda']
Running PythonPipBuilder:ResolveDependencies
Running PythonPipBuilder:CopySource

Build Succeeded

Built Artifacts  : .aws-sam/build
Built Template   : .aws-sam/build/template.yaml

Commands you can use next
=========================
[*] Invoke Function: sam local invoke
[*] Test Function in the Cloud: sam sync --stack-name {stack-name} --watch
[*] Deploy: sam deploy --guided
        
Adams-MacBook-Pro:analytics-black-belt-2021 heyblinkin$ sam deploy

        Deploying with following values
        ===============================
        Stack name                   : hudi-lake
        Region                       : us-east-1
        Confirm changeset            : True
        Disable rollback             : False
        Deployment s3 bucket         : redacted
        Capabilities                 : ["CAPABILITY_IAM", "CAPABILITY_NAMED_IAM", "CAPABILITY_AUTO_EXPAND"]
        Parameter overrides          : {"UseCase": "hudi-lake\n", "CreateNetworkInfrastructure": "TRUE\n", "CreateDmsVpcRole": "TRUE\n", "CreateDmsInfrastructure": "TRUE\n", "CreateQuickSightInfrastructure": "TRUE\n", "OpsEmailAddress": "foo@bar.com\n", "DbName": "*****", "DbEndpoint": "*****", "DbUserNameSpark": "*****", "DBUserNameDms": "awsdms"}
        Signing Profiles             : {}

Initiating deployment
=====================

Waiting for changeset to be created..

CloudFormation stack changeset
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
Operation                                                                               LogicalResourceId                                                                       ResourceType                                                                            Replacement                                                                           
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
+ Add                                                                                   CicdInfrastructureStack                                                                 AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   DataLakeBucketPolicyStack                                                               AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   DataLakeStack                                                                           AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   DmsInfrastructureStack                                                                  AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   EmrPipelineStack                                                                        AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   NetworkInfrastructureStack                                                              AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   QuickSightInfrastructureStack                                                           AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   RuntimeInfrastructureStack                                                              AWS::CloudFormation::Stack                                                              N/A                                                                                   
+ Add                                                                                   SecretsStack                                                                            AWS::CloudFormation::Stack                                                              N/A                                                                                   
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Changeset created successfully. arn:aws:cloudformation:us-west-2:redacted:changeSet/samcli-deploy1643664818/069c4a67-fa20-476d-b1e6-73ecdc568209

Previewing CloudFormation changeset before deployment
======================================================
Deploy this changeset? [y/N]: y

2022-01-31 16:33:59 - Waiting for stack create/update to complete

CloudFormation events from stack operations
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
ResourceStatus                                                                          ResourceType                                                                            LogicalResourceId                                                                       ResourceStatusReason                                                                  
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              NetworkInfrastructureStack                                                              -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              SecretsStack                                                                            -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              CicdInfrastructureStack                                                                 -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              SecretsStack                                                                            Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              NetworkInfrastructureStack                                                              Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              CicdInfrastructureStack                                                                 Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              RuntimeInfrastructureStack                                                              -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              RuntimeInfrastructureStack                                                              Resource creation Initiated                                                           
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              SecretsStack                                                                            -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              CicdInfrastructureStack                                                                 -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              RuntimeInfrastructureStack                                                              -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              NetworkInfrastructureStack                                                              -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DataLakeStack                                                                           -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DataLakeStack                                                                           Resource creation Initiated                                                           
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              DataLakeStack                                                                           -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              EmrPipelineStack                                                                        -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              QuickSightInfrastructureStack                                                           Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DmsInfrastructureStack                                                                  Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              EmrPipelineStack                                                                        Resource creation Initiated                                                           
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              QuickSightInfrastructureStack                                                           -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DmsInfrastructureStack                                                                  -                                                                                                                                                             -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              DmsInfrastructureStack                                                                  -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              QuickSightInfrastructureStack                                                           -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DataLakeBucketPolicyStack                                                               -                                                                                     
CREATE_IN_PROGRESS                                                                      AWS::CloudFormation::Stack                                                              DataLakeBucketPolicyStack                                                               Resource creation Initiated                                                           
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              DataLakeBucketPolicyStack                                                               -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              EmrPipelineStack                                                                        -                                                                                     
CREATE_COMPLETE                                                                         AWS::CloudFormation::Stack                                                              hudi-lake                                                                      -                                                                                     
-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------

Successfully created/updated stack - hudi-lake in us-east-1
```