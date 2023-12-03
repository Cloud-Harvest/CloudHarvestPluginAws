# Data Builder
This utility generates test data for the plugin using the `aws` cli. 

Note that the `aws` binary must be visible to Python/in your `$PATH`.

# Usage
```
usage: data-builder.py [-h] [-f SERVICES_FILE] [-c COUNT] [-w MAX_WORKERS]

options:
  -h, --help            show this help message and exit
  -f SERVICES_FILE, --services-file SERVICES_FILE
                        Location of the services.yaml
  -c COUNT, --count COUNT
                        Number of test records to create per service.
  -w MAX_WORKERS, --max-workers MAX_WORKERS
                        Number of data generation threads to run at once.
```

# Outputs
| Directory   | Description                                                                                                                                             |
|-------------|---------------------------------------------------------------------------------------------------------------------------------------------------------|
| `outputs`   | Randomized data used to perform testing of the api. This data can  be uploaded into a mongo database for testing.                                       |
| `skeletons` | The skeleton returned by the `aws` command. An md5 check compares the files and flags if the skeleton has changed since the last time the tool was run. |


# Example
```
api-plugin-aws/tests/data$ ./data-builder.py 

build: rds.cluster-parameter-group: 1 / 12
cmd  : /usr/bin/aws rds describe-db-cluster-parameter-groups --region us-east-1 --generate-cli-skeleton output
wrote: ./skeletons/rds.cluster-parameter-group.json
wrote: ./outputs/rds.cluster-parameter-group.json

build: rds.cluster-snapshot: 2 / 12
cmd  : /usr/bin/aws rds describe-db-cluster-snapshots --region us-east-1 --generate-cli-skeleton output
wrote: ./skeletons/rds.cluster-snapshot.json
wrote: ./outputs/rds.cluster-snapshot.json
...
```