"""
This library provides functions to assume an AWS role and retrieve temporary credentials. It also includes a caching
mechanism to store the credentials for reuse, reducing the need to repeatedly assume the role which can be time-consuming.

Required AWS Permissions:
- sts:AssumeRole
- organizations:DescribeAccount

"""
from boto3 import Session
from botocore.exceptions import ClientError
from logging import getLogger

logger = getLogger('harvest')

class CachedProfiles:
    profiles = {}


class Profile:
    def __init__(self, account_number: str, role_name: str):
        """
        Initializes a new Profile instance.

        Arguments
        account_number (str): The AWS account number.
        role_name (str): The AWS role name.
        """

        self.account_number = account_number
        self.role_name = role_name

        # Temporary session credentials
        self.aws_access_key_id = None
        self.aws_secret_access_key = None
        self.aws_session_token = None

        self.account_alias = None
        self.expiration = None
        self.role_arn = None

    @property
    def is_expired(self):
        """
        Check if the profile is expired.
        """
        from datetime import datetime, timezone
        return self.expiration < datetime.now(timezone.utc)

    @property
    def credentials(self) -> dict:
        """
        Returns the credentials for the profile in a format acceptable to the boto3 Session.
        Returns:
            dict: A dictionary containing the AWS credentials.
        """

        return {
            'aws_access_key_id': self.aws_access_key_id,
            'aws_secret_access_key': self.aws_secret_access_key,
            'aws_session_token': self.aws_session_token
        }

    def refresh_credentials(self) -> 'Profile':
        """
        Refreshes the credentials for the profile.
        """

        session = Session()
        client = session.client('sts')
        while True:
            try:
                # Assume the role in the specified account
                response = client.assume_role(
                    RoleArn=f'arn:aws:iam::{self.account_number}:role/{self.role_name}',
                    RoleSessionName='CloudHarvest'
                )

                # Extract the temporary credentials from the response
                self.aws_access_key_id = response['Credentials']['AccessKeyId']
                self.aws_secret_access_key = response['Credentials']['SecretAccessKey']
                self.aws_session_token = response['Credentials']['SessionToken']
                self.expiration = response['Credentials']['Expiration']
                self.role_arn = f'arn:aws:iam::{self.account_number}:role/{self.role_name}'

            except ClientError as e:
                # If throttling, sleep for a while and then retry
                if e.response['Error']['Code'] == 'Throttling':
                    from time import sleep
                    sleep(1)

                else:
                    logger.error(f'failed to get credentials for AWS account number {self.account_number}/{self.role_name}: {e.response}')
                    raise e

            else:
                if self.account_alias is None:
                    # If the account alias is not set, try to get it
                    self.get_account_name()
                    break

        return self

    def get_account_name(self):
        """
        Looks up the account alias for a given account number. Assumes the account is part of an organization. If it is not,
        or an error is encountered, the provided account number will be returned.
        """
        from boto3 import Session
        while True:
            try:
                session = Session(**self.credentials)
                client = session.client('organizations')

                response = client.describe_account(AccountId=self.account_number)
                self.account_alias = response['Account']['Name']

            except ClientError as e:
                # If throttling, sleep for a while and then retry
                if e.response['Error']['Code'] == 'Throttling':
                    from time import sleep
                    sleep(1)

                else:
                    logger.error(f'failed to get account name for AWS account number {self.account_number}/{self.role_name}: {e.response}')
                    raise e

            else:
                break

        return self


def get_profile(account_number: str, role_name: str, force_refresh: bool = False) -> Profile:
    """
    Creates or retrieves a profile for a given AWS account and role. If the profile already exists and is not expired, it will
    be returned. If it is expired, the credentials will be refreshed. If the profile does not exist, a new one will be created.
    This function caches the profiles to avoid repeatedly assuming the role.

    Arguments
    account_number (str): The AWS account number.
    role_name (str): The AWS role name.
    force_refresh (bool): If True, forces a refresh of the credentials even if they are not expired.
    """

    # Check if the profile already exists
    if account_number in CachedProfiles.profiles:
        profile = CachedProfiles.profiles[account_number]

        # If the profile is expired, refresh the credentials
        if profile.is_expired or force_refresh:
            profile.refresh_credentials()

    else:
        # Create a new profile and refresh the credentials
        profile = Profile(account_number=account_number, role_name=role_name)
        profile.refresh_credentials()
        CachedProfiles.profiles[account_number] = profile

    return profile
