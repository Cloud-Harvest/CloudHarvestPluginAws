"""
This library provides functions to assume an AWS role and retrieve temporary credentials. It also includes a caching
mechanism to store the credentials for reuse, reducing the need to repeatedly assume the role which can be time-consuming.

Required AWS Permissions:
- sts:AssumeRole
- organizations:DescribeAccount

"""
from logging import getLogger

logger = getLogger('harvest')

class CachedProfiles:
    profiles = {}


def get_profile(account_number: str, role_name: str, profile_name:str = None) -> dict:
    """
    Creates or retrieves a profile for a given AWS account and role. If the profile already exists and is not expired, it will
    be returned. If it is expired, the credentials will be refreshed. If the profile does not exist, a new one will be created.
    This function caches the profiles to avoid repeatedly assuming the role.

    Arguments
    account_number (str): The AWS account number.
    role_name (str): The AWS role name.
    profile_name (str, optional): The AWS profile name.
    """
    from CloudHarvestCoreTasks.environment import Environment
    # Make sure incoming account numbers are properly formatted
    account_number = str(account_number).zfill(12)
    profile = {
        'account_number': account_number,
        'role_name': role_name,
    }

    # Determine the credentials file path from the environment or use the default
    from os.path import expanduser, abspath
    credentials_source = Environment.get(f'platforms.aws.credentials_source')
    credentials_file_path = abspath(expanduser(Environment.get(f'platforms.aws.credentials_file') or '~/.aws/credentials'))

    # Credentials are to be read from a source file like ~/.aws/credentials
    if credentials_source == 'file':
        from os import environ
        environ['AWS_SHARED_CREDENTIALS_FILE'] = credentials_file_path

    # The profile already exists in the cache, so return it
    if account_number in CachedProfiles.profiles.keys():
        profile = CachedProfiles.profiles[account_number]
        return profile

    else:
        from boto3 import Session

        # Handle cases where we're sourcing from a file
        if credentials_source == 'file' and profile_name:
            profile['sourced_from_file'] = True

            logger.debug(f'Retrieving profile `{profile_name}` from {credentials_file_path}.')
            session = Session(profile_name=profile_name)

            # Pull the credentials using sts
            credentials = session.get_credentials()

        # Here we pull directly from the environment, which is the default behavior
        else:
            logger.debug('Retrieving credentials from the environment.')
            session = Session()
            credentials = session.get_credentials()
            profile['sourced_from_file'] = False

    # If a profile is found we will do some extra steps, cache it, and return it.
    if profile and credentials and session:
        profile['credentials'] = {
            'aws_access_key_id': credentials.access_key,
            'aws_secret_access_key': credentials.secret_key,
            'aws_session_token': credentials.token
        }

        # Get the role name sts
        profile['role_arn'] = session.client('sts').get_caller_identity().get('Arn')

        # Apply the role name to the profile from the arn
        profile['role_name'] = profile['role_arn'].split('/')[-1]
        # Get the account alias using the credentials we have for this account
        profile['account_alias'] = get_account_name(account_number=account_number, credentials=profile['credentials'])

        # Cache the profile for future use
        CachedProfiles.profiles[account_number] = profile

    return profile


def get_account_name(account_number: str, credentials: dict) -> str | None:
    """
    Looks up the account alias for a given account number. Assumes the account is part of an organization. If it is not,
    or an error is encountered, the provided account number will be returned.

    Arguments
        account_number (str): The AWS account number.
        credentials (dict): The AWS credentials to use for the session. When not provided, boto3 will attempt to use the default credentials.

    Returns
        str or None: The account alias if found, otherwise None.
    """
    from CloudHarvestPluginAws.tasks.aws import query_aws

    # If an alias is defined in the environment, use that. This is useful for environments where the role cannot access
    # the organization service and the IAM service does not contain a useful alias. Further, some organizations may not
    # want to expose the account name to all users; therefore, a custom alias can be defined in the environment.
    from CloudHarvestCoreTasks.environment import Environment
    result = Environment.get(f'platforms.aws.accounts.{account_number}.alias')

    if result:
        return result

    else:
        logger.debug(f'Failed to get account name for {account_number} using environment. An alias was not defined at `platforms.aws.accounts.{account_number}.alias`')

    # First pass, try the organizations service
    try:
        response = query_aws(
            service='organizations',
            command='describe_account',
            arguments={
                'AccountId': account_number
            },
            credentials=credentials
        )

    except Exception as e:
        logger.debug(f'Failed to get account name for {account_number} using organizations: {e}')

    else:
        return response.get('Name')

    # Second pass, try the IAM service
    try:
        response = query_aws(
            service='iam',
            command='list_account_aliases',
            arguments={},
            credentials=credentials
        )

        if response:
            # If there are multiple aliases, return the first one that does not contain the account number
            for alias in response:
                if account_number not in alias:
                    result = alias
                    break

    except Exception as e:
        logger.debug(f'Failed to get account name for {account_number} using iam: {e}')

    else:
        if result:
            return result

        else:
            logger.debug(f'Failed to get account name for {account_number} using iam because no appropriate alias was found')

    # If no alias is found, return the account number
    return account_number
