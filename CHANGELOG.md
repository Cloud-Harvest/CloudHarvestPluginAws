# CHANGELOG

## 0.4.0
- [get_credentials() will check the AWS credentials file for profiles](https://github.com/Cloud-Harvest/CloudHarvestPluginAws/issues/20)
  - Added the `platforms.aws.credentials_source` configuration option; when `file`, the AWS credentials file will be checked for profiles
  - The `Profile` class can now write to the AWS credentials file
  - `get_credentials()` may now check the AWS credentials file for profiles

## 0.3.2
- [Platform configuration needs to allow different role names per account](https://github.com/Cloud-Harvest/CloudHarvestAgent/issues/10)
- Updated to conform with CloudHarvestCoreTasks 0.6.6

## 0.3.1
- Updated to conform with CloudHarvestCoreTasks 0.6.5

## 0.3.0
- Updated to conform with CloudHarvestCoreTasks 0.6.4
- Added reports/services
- Updated reports/services
- Fixed an issue where an AWS account number could be passed as int with an incorrect number of leading zeros

## 0.2.0
- Updated to conform with CloudHarvestCoreTasks 0.6.0
- Updated standard which places all report/service templates into the 'templates' directory
- Imports are now absolute
- Removed the `authenticators` directory and its files to avoid confusion pending future implementation
- Updated the `AwsTask` to accept a true `PSTAR` configuration and self-populate/cache credentials
- Added the `credentials` file which performs `sts-assume-role` operations and caches profile information
- Added some `lightsail` reports/services to the `templates` directory
- Added `tests`

## 0.1.5
- Updated to CloudHarvestCorePluginManager 0.3.1
- Updates to conform to CloudHarvestCoreTasks 4.2

## 0.1.4
- Updates to conform to CloudHarvestCoreTasks 4.0
- Implemented AWS IAM authentication
- `AwsTask` now accepts `credentials`

## 0.1.3
- Update to conform with 
  - CloudHarvestCorePluginManager 0.2.4
  - CloudHarvestCoreTasks 0.3.1
- Added the `services` directory which contains instructions on how to harvest data from AWS
- Added README files for each object category

## 0.1.2
- Updated to conform with CloudHarvestCorePluginManager 0.2.0
- Added this CHANGELOG
