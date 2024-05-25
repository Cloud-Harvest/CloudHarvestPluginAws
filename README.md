# CloudHarvestPluginAws
This repository contains the AWS plugin for the CloudHarvest API. This plugin is responsible for interfacing with the AWS API and providing data to the CloudHarvest API.

# Table of Contents
- [CloudHarvestPluginAws](#CloudHarvestPluginAws)
- [Usage](#Usage)
- [License](#License)

# Usage
```yaml
task_chain:
  
  tasks:
    # Stage 1: collect data from the BOTO3 API
    - aws:
        name: 'aws'
        description: 'Get information about the AWS account'
        result_as: boto_result
        service: rds
        command: describe_db_instances
        arguments:
          - DBInstanceIdentifier: 'mydbinstance'
          - Filters:
              - Name: 'db-instance-id'
                Values:
                  - 'mydbinstance'

    # Stage 2: modify the data by converting it into a HarvestRecordSet
    # RecordSetTask from https://github.com/Cloud-Harvest/CloudHarvestCoreDataModel/
    - recordset:
        name: 'recordset'
        description: 'Modify the AWS data into a recordset'
        result_as: recordset
        recordset_name: boto_result
        function: modify_records
        arguments:
          function: key_value_list_to_dict
          arguments:
            source_key: Tags

        

```

# License
Shield: [![CC BY-NC-SA 4.0][cc-by-nc-sa-shield]][cc-by-nc-sa]

This work is licensed under a
[Creative Commons Attribution-NonCommercial-ShareAlike 4.0 International License][cc-by-nc-sa].

[![CC BY-NC-SA 4.0][cc-by-nc-sa-image]][cc-by-nc-sa]

[cc-by-nc-sa]: http://creativecommons.org/licenses/by-nc-sa/4.0/
[cc-by-nc-sa-image]: https://licensebuttons.net/l/by-nc-sa/4.0/88x31.png
[cc-by-nc-sa-shield]: https://img.shields.io/badge/License-CC%20BY--NC--SA%204.0-lightgrey.svg