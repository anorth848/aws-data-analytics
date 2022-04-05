check_defined = \
    $(strip $(foreach 1,$1, \
        $(call __check_defined,$1,$(strip $(value 2)))))
__check_defined = \
    $(if $(value $1),, \
      $(error Undefined $1$(if $2, ($2))))

build: clean mkdirs download scripts

clean:
	rm -rf build

mkdirs:
	mkdir -p build/emr/jars

scripts:
	cp -r src/emr/ build/emr/ ;

download:
	curl https://jdbc.postgresql.org/download/postgresql-42.3.1.jar -o build/emr/jars/postgresql-42.3.1.jar ;\

deploy: $(call check_defined, STACK_NAME)
deploy:
	BUCKET=`aws --region $(REGION) ssm get-parameter --name /$(STACK_NAME)/cicd/artifact_bucket/name | jq -r .Parameter.Value ` ;\
	aws --region $(REGION) s3 sync build s3://$$BUCKET/artifacts/ --include '*' --exclude '*__pycache__*' --delete  ;

enable_jdbc: $(call check_defined, STACK_NAME)
	RULE=`aws --region $(REGION) ssm get-parameter --name /$(STACK_NAME)/emr_pipeline/event_rule/jdbc_load/name | jq -r .Parameter.Value` ;\
	aws --region $(REGION) events enable-rule --name $$RULE && echo "enable_jdbc complete"

enable_incremental: $(call check_defined, STACK_NAME)
	RULE=`aws --region $(REGION) ssm get-parameter --name /$(STACK_NAME)/emr_pipeline/event_rule/incremental_hudi/name | jq -r .Parameter.Value` ;\
	aws --region $(REGION) events enable-rule --name $$RULE && echo "enable_incremental complete"
