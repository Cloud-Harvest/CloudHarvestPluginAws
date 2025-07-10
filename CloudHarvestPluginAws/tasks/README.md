# AwsTask([BaseTask](https://github.com/Cloud-Harvest/CloudHarvestCoreTasks/blob/main/docs/tasks/base_task.md)) | `aws`
This task performs some action against the AWS API using the [boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html)
client.

## Directives

| Directive         | Required | Default | Description                                                                                                                                                                                      |
|-------------------|----------|---------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|
| command           | Yes      |         | The boto3 command to execute.                                                                                                                                                                    |
| arguments         | No       |         | Command arguments to include.                                                                                                                                                                    |
| service           | No       |         | The AWS Service.                                                                                                                                                                                 |
| type              | No       |         | A Harvest convention which identifies the service sub-type, such as an RDS **Instance** or **Cluster**.                                                                                          |
| account           | No       |         | The AWS Account **number**.                                                                                                                                                                      |
| region            | No       |         | The AWS Account region.                                                                                                                                                                          |
| role              | No       |         | The AWS Account role name to use when provisioning credentials.                                                                                                                                  |
| include_metadata  | No       | `True`  | When True, some 'Harvest' metadata fields are added to the result.                                                                                                                               |
| global_service    | No       | `False` | When provided, negates any `region` input and the `command` is submitted without a region identifier. Necessary for some service/types such as `Route53 Hosted Zones` which are global services. |
| max_retries       | No       | `10`    | Maximum times Harvest will attempt to perform the boto3 command if it hits a Throttling error. All other errors are fatal.                                                                       |
| result_path       | No       |         | Path to the results. When not provided, the path is the first key that is not 'Marker' or 'NextToken'.                                                                                           |

> For the purposes of writing a service template, the `service`, `type`, `account`, `region`, and `role` fields are 
> not required. They are automatically populated by the API when the task is queued. This was done to reduce toil when
> writing service templates. However, these fields may be required in other scenarios.

## Example

```yaml
- name: aws
  command: ec2.describe_instances
  arguments:
    Filters:
      - Name: instance-state-name
        Values:
          - running
  include_metadata: true
  max_retries: 10
```