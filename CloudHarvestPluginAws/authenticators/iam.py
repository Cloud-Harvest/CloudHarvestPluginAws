from CloudHarvestCorePluginManager.decorators import register_definition

class AssumedRoles:
    roles = {}

    @staticmethod
    def _auto_purge_thread():
        from time import sleep
        from datetime import datetime

        while True:
            [
                AssumedRoles.roles.pop(account_role)
                for account_role, credentials in AssumedRoles.roles.items()
                if datetime.fromisoformat(credentials['Expiration']) < datetime.now()
            ]

            sleep(1)

            AssumedRoles.purge()

    @staticmethod
    def add(account_number: str, role_name: str, credentials: dict):
        AssumedRoles.roles[f'{account_number}/{role_name}'] = credentials

    @staticmethod
    def get(account_number: str, role_name: str):
        return AssumedRoles.roles.get(f'{account_number}/{role_name}', None)

    @staticmethod
    def remove(account_number: str, role_name: str):
        AssumedRoles.roles.pop(f'{account_number}/{role_name}', None)

    @staticmethod
    def purge():
        AssumedRoles.roles = {}


@register_definition
class AssumeRoleTask:
    """
    This class is used to assume an AWS IAM role. It takes an account number, role name, profile, and region as inputs.
    The `run` method is used to assume the role and store the result.

    Args:
        account_number (str): The AWS account number.
        role_name (str): The name of the IAM role to assume.
        profile (str, optional): The AWS profile to use. Defaults to None.
        region (str, optional): The AWS region to use. Defaults to None.
    """

    def __init__(self, account_number: str, role_name: str, profile: str = None, region: str = None):
        self.account_number = account_number
        self.role_name = role_name
        self.profile_name = profile
        self.region_name = region
        self.result = None

    def __enter__(self):
        # Return the instance when used in a context manager
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        # Handle the exit from a context manager, no specific actions needed here
        return None

    def run(self) -> 'AssumeRole':
        """
        Assume the specified IAM role using the provided account number, role name, profile, and region.
        The result of the assume role operation is stored in the `result` attribute.

        Returns:
            AssumeRole: The instance of the class.
        """
        from tasks import AwsTask

        # Use the AwsTask class to assume the role
        with AwsTask(profile=self.profile_name,
                     region=self.region_name,
                     service='sts',
                     command='assume-role',
                     result_key='Credentials',
                     arguments={
                         'RoleArn': f'arn:aws:iam::{self.account_number}:role/{self.role_name}',
                         'RoleSessionName': 'harvest-api-plugin-aws'
                     }) as task:

            # Run the task
            task.run()

            from copy import copy
            # Copy the result of the task to the `result` attribute
            self.result = copy(task.result)

        # Return the instance of the class
        return self
