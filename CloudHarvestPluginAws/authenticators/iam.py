from logging import getLogger
from typing import List

logger = getLogger('harvest')

class Credentials:
    """
    An index of AwsCredentials. The index is used to quickly find credentials by profile name, account ID, or ARN.
    """

    index = {
        'by_profile_name': {},
        'by_account_id': {},
        'by_arn': {}
    }

    @staticmethod
    def add(credential: 'Credential', override_profile_name: str = None):
        """
        Add a credential to the index.

        Args:
            credential (Credential): The credential to add.
            override_profile_name (str, optional): The profile name to use instead of the credential's profile name. Default is None.
        """

        # If the profile name is not set, look up the role ARN.
        if not credential.profile_name:
            credential.lookup_role_arn()

        # If the override_profile_name is not provided, use the credential's profile name.
        profile_name = override_profile_name or credential.profile_name

        Credentials.index['by_profile_name'][profile_name] = credential
        Credentials.index['by_account_id'][credential.account_id] = credential
        Credentials.index['by_arn'][credential.aws_role_arn] = credential

    @staticmethod
    def clear():
        """
        Clear the index of Credentials.
        """
        Credentials.index = {
            'by_profile_name': {},
            'by_account_id': {},
            'by_arn': {}
        }

    @staticmethod
    def delete(profile_name: str = None, account_id: str = None, arn: str = None):
        """
        Delete a credential from all indexes.

        Args:
            profile_name (str, optional): The profile name. Default is None.
            account_id (str, optional): The account ID. Default is None.
            arn (str, optional): The ARN. Default is None.
        """

        credential = None
        if profile_name:
            credential = Credentials.get(profile_name=profile_name)

        elif account_id:
            credential = Credentials.get(account_id=account_id)

        elif arn:
            credential = Credentials.get(arn=arn)

        if credential:
            del Credentials.index['by_profile_name'][credential.profile_name]
            del Credentials.index['by_account_id'][credential.account_id]
            del Credentials.index['by_arn'][credential.aws_role_arn]

    @staticmethod
    def get(profile_name: str = None, account_id: str = None, arn: str = None) -> 'Credential':
        """
        Get a credential from the index.

        Args:
            profile_name (str, optional): The profile name. Default is None.
            account_id (str, optional): The account ID. Default is None.
            arn (str, optional): The ARN. Default is None.
        """

        if profile_name:
            return Credentials.index['by_profile_name'].get(profile_name)

        elif account_id:
            return Credentials.index['by_account_id'].get(account_id)

        elif arn:
            return Credentials.index['by_arn'].get(arn)


class Credential:
    def __init__(self):
        # Identities
        self.aws_role_arn = None
        self.aws_role_session_name = None

        # Credentials
        self.aws_access_key_id = None
        self.aws_secret_access_key = None
        self.aws_session_token = None

        # Data
        self.account_id = None
        self.account_name = None
        self.aws_role_duration_seconds = None
        self.token_create_datetime = None


    @property
    def boto_session_map(self) -> dict:
        """
        Get the Boto3 session map for the credentials.

        Example:
            >>> # Create a new credential.
            >>> credential = Credential()
            >>> credential.aws_access_key_id = 'AKIA...'
            >>> credential.aws_secret_access_key = '...'
            >>> credential.aws_session_token = '...'
            >>>
            >>> # Get the Boto3 session map.
            >>> credential.boto_session_map
            >>> {
            >>>     'aws_access_key_id': 'AKIA...',
            >>>     'aws_secret_access_key': '...',
            >>>     'aws_session_token': '...'
            >>> }
            >>>
            >>> # Use the Boto3 session map to create a new session.
            >>> from boto3 import Session
            >>> session = Session(**credential.boto_session_map)
        """

        return {
            'aws_access_key_id': self.aws_access_key_id,
            'aws_secret_access_key': self.aws_secret_access_key,
            'aws_session_token': self.aws_session_token
        }

    @property
    def has_credentials(self) -> bool:
        return self.aws_access_key_id and self.aws_secret_access_key

    @property
    def is_expired(self) -> bool or None:
        """
        Check if the credentials are expired. To determine if the credentials are expired, the token_create_datetime and
        aws_role_duration_seconds must be set. Otherwise, the result is always None.
        """

        from datetime import datetime, timezone

        if self.aws_role_duration_seconds and self.token_create_datetime:
            return self.token_create_datetime + self.aws_role_duration_seconds < datetime.now(timezone.utc)

        else:
            return False

    @property
    def profile_name(self) -> str or None:
        """
        The profile name for the credentials is generated from a lowercase representation of the account name and role ARN.

        If the account_name or aws_role_arn is not set, the profile_name is None.

        Example:
            >>> # Create a new credential.
            >>> credential = Credential()
            >>> credential.account_name = 'MyAccount'
            >>> credential.aws_role_arn = 'arn:aws:iam::123456789012:role/MyRole'
            >>>
            >>> # Get the profile name.
            >>> credential.profile_name
            >>> 'harvest-myaccount-myrole'
        """
        result = None

        try:
            '-'.join(
                [
                    'harvest-aws',
                    self.account_name,
                    self.aws_role_arn.split("/")[-1]
                ]).lower()

        finally:
            return result

    @property
    def role_name(self) -> str or None:
        try:
            return str(self.aws_role_arn.split('/')[-1]).lower()

        finally:
            return None

    def lookup_duration(self, requestor: dict) -> int:
        """
        Look up the role duration. If the role duration is not set, the duration is fetched from the AWS API and set.
        """

        if not self.aws_role_duration_seconds:
            from boto3 import Session
            session = Session(**Credentials.get(**requestor).boto_session_map)
            client = session.client('iam')
            result = client.get_role(RoleName=self.role_name).get('Role').get('MaxSessionDuration')

            self.aws_role_duration_seconds = result

        return self.aws_role_duration_seconds

    def lookup_credentials(self,
                           requesting_profile_name: str = None,
                           requesting_credentials: 'Credential' = None,
                           max_duration_seconds: int = 43200,
                           retries: int = 12) -> dict:
        """
        Get the role credentials. When no requesting profile or credentials are provided, the default profile / system IAM
        role is used.

        Args:
            requesting_profile_name (str, optional): The requesting profile name. Default is None.
            requesting_credentials (Credential, optional): The requesting credentials. Default is None.
            max_duration_seconds (int, optional): The maximum duration in seconds. Default is 43200.
            retries (int, optional): The number of retries. Default is 12.
        """

        from boto3 import Session

        # Make the request using a profile stored in the AWS configuration file.
        if requesting_profile_name:
            session = Session(profile_name=requesting_profile_name)

        # Make the request using the provided credentials.
        elif requesting_credentials:
            session = Session(**requesting_credentials.boto_session_map)

        # Make the request using the default profile.
        else:
            session = Session()

        i = 0
        i_max_seconds = max_duration_seconds

        while i < retries:
            try:
                client = session.client('sts')
                response = client.assume_role(RoleArn=self.aws_role_arn,
                                              RoleSessionName='harvest-session',
                                              DurationSeconds=self.aws_role_duration_seconds or i_max_seconds)

            except Exception as e:
                logger.error(f'Failed to assume role: {e}')

                # Increment the retry counter and calculate the new duration to attempt.
                i += 1
                i_max_seconds = max_duration_seconds / (i * 3600)

                # Wait before retrying to mitigate rate limiting.
                from time import sleep
                sleep(.5)

            else:
                self.aws_session_token = response['Credentials']['SessionToken']
                self.aws_access_key_id = response['Credentials']['AccessKeyId']
                self.aws_secret_access_key = response['Credentials']['SecretAccessKey']

                return self.boto_session_map

    def lookup_role_arn(self) -> str:
        """
        Get the AWS role ARN from the credentials.
        """

        if self.aws_role_arn:
            return self.aws_role_arn

        from boto3 import Session

        session = Session(**self.boto_session_map)

        client = session.client('sts')
        response = client.get_caller_identity()

        self.account_id = response['Account']
        self.aws_role_arn = response['Arn']

        return self.account_id


