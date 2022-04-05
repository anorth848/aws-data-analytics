# Use case specific documentation

## import_config_data.py    

This can be used to import the configuration data into DynamoDB for the hammerdb source database
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python import_config_data.py --table_name <your dynamodb table name>
```

## export_config_data.py

This can be used to export the configuration data from DynamoDB once you have it properly configured
```
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python export_config_data.py --table_name <your dynamodb table name>
```

## reports.yaml   

This stack can be created to create hammerdb specific reports in Quicksight

```
aws cloudformation create-stack --stack-name hammerdb-reports --template-body file://reports.yaml --capabilities CAPABILITY_AUTO_EXPAND
```
*Note: It assumes the parent stack name, so adjust parameters accordingly*



