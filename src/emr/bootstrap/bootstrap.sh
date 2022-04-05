#!/usr/bin/env bash
set -e

ARTIFACT_PREFIX_URI=$1
RUNTIME_PREFIX_URI=$2

sudo aws s3 sync ${ARTIFACT_PREFIX_URI}/emr/jars/ /usr/lib/spark/jars/

is_master=$(cat /mnt/var/lib/info/instance.json | jq .isMaster)
if [ $is_master = true ]
then
    sudo aws s3 sync ${ARTIFACT_PREFIX_URI}/emr/scripts/ /mnt/var/lib/instance-controller/public/scripts/ && sudo chmod -R 755 $_
    sudo aws s3 sync ${RUNTIME_PREFIX_URI} /mnt/var/lib/instance-controller/public/runtime_configs/ && sudo chmod -R 755 $_
    sudo pip3 install boto3==1.20.24
fi
