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

    auto_refresh_thread = None

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

        result = None
        # Look up the credential by profile name, account ID, or ARN. Return the first matching index.
        if profile_name and Credentials.index['by_profile_name'].get(profile_name):
            result = Credentials.index['by_profile_name'].get(profile_name)

        elif account_id and Credentials.index['by_account_id'].get(account_id):
            result = Credentials.index['by_account_id'].get(account_id)

        elif arn and Credentials.index['by_arn'].get(arn):
            result = Credentials.index['by_arn'].get(arn)

        return result

    @staticmethod
    def start_auto_refresh(worker_refresh_rate: int = 60):
        """
        Start the auto-refresh thread for the index.
        """

        from threading import Thread
        from time import sleep

        def auto_refresh():
            while True:
                for profile_name, credential in Credentials.index['by_profile_name'].items():
                    if credential.is_expired:
                        credential.lookup_credentials(requesting_profile_name='default')

                sleep(worker_refresh_rate)

        Credentials.auto_refresh_thread = Thread(target=auto_refresh)
        Credentials.auto_refresh_thread.start()

class Credential:
    """
    A class to manage AWS credentials. The Credential class is used to store and manage AWS credentials for Harvest.
    These values are not assigned on instantiation because there are many paths to populating credentials. Instead,
    the Credential class provides methods to look up and set the credentials.

    Attributes:
        aws_access_key_id (str): The AWS access key ID.
        aws_role_arn (str): The Amazon Resource Name (ARN) of the AWS role.
        aws_role_session_name (str): The session name for the AWS role.
        aws_secret_access_key (str): The AWS secret access key.
        aws_session_token (str): The AWS session token.
        account_id (str): The AWS account ID.
        account_name (str): The name of the AWS account.
        aws_role_duration_seconds (int): The duration, in seconds, for which the role credentials are valid.
        token_create_datetime (datetime): The datetime when the session token was created.
        requestor (str): The ARN of the role that requested the credentials.
        auto_refresh (bool): If True, the credentials are automatically refreshed via the Credentials start_auto_refresh() method.

    Properties:
        boto_session_map (dict): The Boto3 session map for the credentials.
        has_credentials (bool): Check if the credentials have been set.
        is_expired (bool): Check if the credentials are expired.
        profile_name (str): The profile name for the credentials.
        role_name (str): The role name for the credentials.
    """
    def __init__(self, **kwargs):
        # Identities
        self.aws_role_arn = None
        self.aws_role_session_name = None

        # Credentials
        self.aws_access_key_id = None
        self.aws_secret_access_key = None
        self.aws_session_token = None
        self.aws_secret_expiration = None

        # Data
        self.account_id = None
        self.account_name = None
        self.aws_role_duration_seconds = None
        self.token_create_datetime = None
        self.requestor = None
        self.auto_refresh = False

        # Set the attributes from the keyword arguments.
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)

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
        Check if the credentials are expired. We check several conditions to determine if the credentials are expired.
        1. If the aws_secret_expiration is set and the expiration is less than the current time, the credentials are expired.
        2. If the aws_role_duration_seconds and token_create_datetime are set and the duration has passed, the credentials are expired.

        If none of these conditions are met, the credentials are not expired.
        """

        from datetime import datetime, timezone

        if self.aws_secret_expiration:
            return self.aws_secret_expiration < datetime.now(timezone.utc)

        elif self.aws_role_duration_seconds and self.token_create_datetime:
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
                from datetime import datetime, timezone

                self.aws_session_token = response['Credentials']['SessionToken']
                self.aws_access_key_id = response['Credentials']['AccessKeyId']
                self.aws_secret_access_key = response['Credentials']['SecretAccessKey']
                self.aws_secret_expiration = response['Credentials']['Expiration']
                self.token_create_datetime = datetime.now(timezone.utc)
                self.requestor = requesting_profile_name

                return self.boto_session_map


    def lookup_duration(self, requestor: dict) -> int:
        """
        Look up the role duration. If the role duration is not set, the duration is fetched from the AWS API and set.
        """

        # Only look up the role duration if it is not set.
        if not self.aws_role_duration_seconds:
            from boto3 import Session
            session = Session(**Credentials.get(**requestor).boto_session_map)
            client = session.client('iam')
            result = client.get_role(RoleName=self.role_name).get('Role').get('MaxSessionDuration')

            self.aws_role_duration_seconds = result

        return self.aws_role_duration_seconds

    def lookup_role_arn(self) -> str:
        """
        Get the AWS role ARN from STS if it is not set. Otherwise, return the set role ARN.
        """

        # Only look up the role ARN if it is not set.
        if self.aws_role_arn:
            return self.aws_role_arn

        from boto3 import Session

        session = Session(**self.boto_session_map)

        client = session.client('sts')
        response = client.get_caller_identity()

        self.account_id = response['Account']
        self.aws_role_arn = response['Arn']

        return self.account_id


def lookup_assumable_roles(profile_name = 'default') -> List[str]:
    """
    Look up the assumable roles for a profile. This function is intended to work with the default role attached to an
    EC2 instance or similar AWS service which can assume roles. Once the assumable roles are found, use the
    lookup_credentials method to assume the role and get the tokens.

    Args:
        profile_name (str, optional): The profile name. Default is 'default'.

    Example:
        >>> # This example follows the code chain necessary to get the credentials from an EC2 instance, then assume
        >>> # all the credentials that the instance can assume.
        >>> admin_credentials = Credential()
        >>> admin_credentials.lookup_credentials()
        >>>
        >>> # Look up the assumable roles.
        >>> arns = lookup_assumable_roles(profile_name=admin_credentials.profile_name)
        >>> [
        >>>     'arn:aws:iam::123456789012:role/MyRole',
        >>>     'arn:aws:iam::123456789012:role/MyOtherRole'
        >>> ]
        >>>
        >>> for arn in arns:
        >>>     # Create Credential objects for each Arn
        >>>     credential = Credential()
        >>>     credential.aws_role_arn = arn
        >>>
        >>>     # Get the credentials for the role
        >>>     credential.lookup_credentials(requesting_profile_name=admin_credentials.profile_name)
        >>>
        >>>     # Add the credentials to the index
        >>>     Credentials.add(credential)
    """

    from boto3 import Session

    credential = Credentials.get(profile_name=profile_name)
    session = Session(**credential.boto_session_map)
    client = session.client('sts')

    # List all roles
    roles = client.list_roles()

    assumable_roles = []

    # Check the trust relationships of each role
    for role in roles['Roles']:
        assume_role_policy = role['AssumeRolePolicyDocument']
        for statement in assume_role_policy['Statement']:
            if statement['Effect'] == 'Allow' and 'AWS' in statement['Principal']:

                # Add the role ARN to the list if the current role is allowed to assume it
                assumable_roles.append(role['Arn'])

    return assumable_roles
