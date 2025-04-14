"""
This library provides functions to assume an AWS role and retrieve temporary credentials. It also includes a caching
mechanism to store the credentials for reuse, reducing the need to repeatedly assume the role which can be time-consuming.

Required AWS Permissions:
- sts:AssumeRole
- organizations:DescribeAccount

"""


class CachedProfiles:
    profiles = {}


def assume_role(account_number: str, role_name: str) -> dict:
    """
    Retrieves temporary credentials for a given AWS account and role.

    Arguments
    account_number (str): The AWS account number.
    role_name (str): The AWS role name.
    """

    from boto3 import Session
    from botocore.exceptions import ClientError

    session = Session()
    client = session.client('sts')
    try:
        # Assume the role in the specified account
        response = client.assume_role(
            RoleArn=f'arn:aws:iam::{account_number}:role/{role_name}',
            RoleSessionName='CloudHarvest'
        )

        # Extract the temporary credentials from the response
        credentials = {
            'aws_access_key_id': response['Credentials']['AccessKeyId'],
            'aws_secret_access_key': response['Credentials']['SecretAccessKey'],
            'aws_session_token': response['Credentials']['SessionToken'],
            'expiration': response['Credentials']['Expiration'],
            'account_number': account_number,
            'role_name': role_name,
            'role_arn': f'arn:aws:iam::{account_number}:role/{role_name}'
        }

    except ClientError as e:
        # Handle errors related to assuming the role
        raise e

    else:
        # Return the temporary credentials
        return credentials


def get_credentials(account_number: str, role_name: str) -> dict:
    """
    Retrieves temporary credentials for a given AWS account and role.

    Arguments
    account_number (str): The AWS account number.
    role_name (str): The AWS role name.
    """

    returnable_keys = ('aws_access_key_id', 'aws_secret_access_key', 'aws_session_token')

    # Check if the profile is already cached
    if account_number in CachedProfiles.profiles:
        # Check if the cached credentials are still valid
        from datetime import datetime, timezone
        if CachedProfiles.profiles[account_number]['expiration'] > datetime.now(timezone.utc):

            # Return the cached credentials
            return {k:v
                for k, v in CachedProfiles.profiles[account_number].items()
                if k in returnable_keys
            }

        return CachedProfiles.profiles[account_number]

    # If not, assume the role and cache the credentials
    credentials = assume_role(account_number=account_number, role_name=role_name)
    CachedProfiles.profiles[account_number] = credentials
    CachedProfiles.profiles[account_number]['account_alias'] = lookup_account_name(account_number)

    # We have to restrict the return keys to only those accepted by the boto3 Session. Other keys, such as
    # 'expiration' are not accepted and will raise an error.
    return {
        key: value
        for key, value in credentials.items()
        if key in returnable_keys
    }


def lookup_account_name(account_number: str) -> str:
    """
    Looks up the account alias for a given account number. Assumes the account is part of an organization. If it is not,
    or an error is encountered, the provided account number will be returned.

    Arguments:
        account_number (str): The AWS account number.

    Returns:
        str: The account name.
    """
    from boto3 import Session

    name = None

    try:
        # Create a session and client for IAM
        cached_account = CachedProfiles.profiles[account_number]

        session = Session(
            aws_access_key_id=cached_account['aws_access_key_id'],
            aws_secret_access_key=cached_account['aws_secret_access_key'],
            aws_session_token=cached_account['aws_session_token'],
        )

        client = session.client('organizations')

        response = client.describe_account(AccountId=account_number)
        name = response['Account']['Name']

    except Exception as ex:
        pass

    finally:
        # Return the name or the account number if the name is not found
        return name or account_number
