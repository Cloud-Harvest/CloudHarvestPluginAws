# Services

# File Format
For file names, use the following format: `provider.service.type.py`.  As an example, `aws.ec2.instances.py` would be 
the file name for a service that interacts with AWS EC2 instances.

# Service File Structure
Each service file should begin with the `harvest` keyword and a description of the service, followed by the configurations
for that service.

```yaml
harvest:
  name: AWS EC2 Instances
  description: This service harvests data from AWS EC2 instances
  platform: aws
  service: ec2
  type: instances
  
  tasks:
    all:
      # Gather the ec2 instances from AWS
      - aws:  &describe_instances
          name: Retrieve Instances 
          command: describe_instances
          result_key: Reservations
          result_as: describe_instances_result
          unique_identifier_keys: 
              - InstanceId

      - recordset:  &modify_records
          name: Modify Records
          description: Change the records to a more usable format
          result_as: unwound_instances
          stages:
              # Creates one record for each instance
              - unwind:
                  source_key: Instances
            
              # Convert the tags to a dict
              - key_value_list_to_dict:
                  source_key: Tags

    single:  
      - <<: *describe_instances
        arguments:
            instance_ids: 
                - var.record.InstanceId

      - <<: *modify_records

```
