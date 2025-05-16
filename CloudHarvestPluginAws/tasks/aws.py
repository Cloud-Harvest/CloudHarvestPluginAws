from CloudHarvestCoreTasks.dataset import WalkableDict
from CloudHarvestCoreTasks.tasks import BaseTask
from CloudHarvestCorePluginManager.decorators import register_definition

from botocore.exceptions import ClientError


@register_definition(name='aws', category='task')
class AwsTask(BaseTask):
    def __init__(self,
                 command: str,
                 arguments: dict = None,
                 service: str = None,
                 type: str = None,
                 account: str = None,
                 role: str = None,
                 region: str = None,
                 include_metadata: bool = True,
                 max_retries: int = 10,
                 result_path: str or list or tuple = None,
                 *args,
                 **kwargs):
        """
        Constructs all the necessary attributes for the AwsTask object.

        Args:
            command (str): The command to execute on the AWS service.
            arguments (dict): The arguments to pass to the command. Defaults to empty dictionary.
            service (str, optional): The AWS service to interact with (e.g., 's3', 'ec2'). If not specified, the default is pulled from the task chain variables.
            type (str, optional): The type of the AWS service (e.g., 's3', 'ec2'). If not specified, the default is pulled from the task chain variables.
            account (str, optional): The AWS number to use for the session. If not specified, the default is pulled from the task chain variables.
            role (str, optional): The AWS role to use for the session. If not specified, the default is pulled from the environment variables.
            region (str, optional): The AWS region to use for the session. None is supported as not all AWS services require a region. If not specified, the default is pulled from the task chain variables.
            include_metadata (bool, optional): When True, some 'Harvest' metadata fields are added to the result. Defaults to True.
            max_retries (int, optional): The maximum number of retries for the command. Defaults to 10.
            result_path (str, optional): Path to the results. When not provided, the path is the first key that is not 'Marker' or 'NextToken'.
        """

        # Initialize parent class
        super().__init__(*args, **kwargs)

        # Set STAR: Service, Type, Account, Region
        self.service = service or self.task_chain.variables.get('service')
        self.type = type or self.task_chain.variables.get('type')
        self.account = str(account or self.task_chain.variables.get('account')).zfill(12)   # AWS Account Numbers are 12 digit strings with leading zeros
        self.region = region or self.task_chain.variables.get('region')

        # boto3 session and client inputs
        from CloudHarvestCoreTasks.environment import Environment
        self.role = role or Environment.get(name=f'platforms.aws.accounts.{self.account}.role') or Environment.get('platforms.aws.default_role')
        self.command = command
        self.arguments = arguments or {}
        self.max_retries = max_retries

        # Output manipulation
        self.include_metadata = include_metadata
        self.result_path = result_path

        # Programmatic attributes
        self.account_alias = None

        # Initialize parent class again
        super().__init__(*args, **kwargs)

    def method(self):
        """
        Executes the command on the AWS service and stores the result.

        Raises:
            Exception: If the maximum number of retries is exceeded or no result is returned from the command.

        Returns:
            self: Returns the instance of the AwsTask.
        """
        from CloudHarvestPluginAws.credentials import Profile, get_profile
        profile: Profile = get_profile(account_number=self.account, role_name=self.role)

        # Set the account_alias attribute
        self.account_alias = profile.account_alias

        # Execute the AWS query
        result = query_aws(
            service=self.service,
            region=self.region,
            command=self.command,
            arguments=self.arguments,
            credentials=profile.credentials,
            max_retries=self.max_retries,
            result_path=self.result_path
        )

        # Add starting metadata to the result
        if self.include_metadata:
            if isinstance(result, list):
                for record in result:
                    if isinstance(record, dict):
                        record['Harvest'] = {
                            'AccountId': self.account,
                            'AccountName': self.account_alias
                        }

            elif isinstance(result, dict):
                result['Harvest'] = {
                    'AccountId': self.account,
                    'AccountName': self.account_alias
                }

        # Store the result
        self.result = result

        # Return the instance of the AwsTask
        return self


def query_aws(service: str,
              command: str,
              arguments: dict,
              credentials: dict = None,
              max_retries: int = None,
              region: str = None,
              result_path: str or list or tuple = None) -> WalkableDict:
    """
    Queries AWS for the specified service and command.

    Arguments
        service (str): The AWS service to query (e.g., 's3', 'ec2').
        command (str): The command to execute on the AWS service.
        arguments (dict): The arguments to pass to the command.
        credentials (dict, optional): The AWS credentials to use for the session. When not provided, boto3 will attempt to use the default credentials.
        max_retries (int, optional): The maximum number of retries for the command. Defaults to 10.
        region (str, optional): The AWS region to use for the session. None is supported as not all AWS services require a region.
        result_path (str, optional): Path to the results. When not provided, the path is the first key that is not 'Marker' or 'NextToken'.

    Returns:
        Any: The result of the AWS query.
    """
    # Make sure the credentials is a dictionary
    credentials = credentials or {}

    from boto3 import Session
    session = Session(**credentials)

    # Create a client for the specified service in the specified region
    client = session.client(service_name=service, region_name=region)

    # Initialize the result and attempt counter
    attempt = 0

    # Make sure the command exists in the client before making any attempts
    if not hasattr(client, command):
        raise Exception(f'Command `{command}` not found in service `{service}`')

    # Start a loop to execute the command
    while True:
        # Increment the attempt counter
        attempt += 1

        try:
            # If the maximum number of retries is exceeded, raise an exception
            if attempt > max_retries:
                raise Exception('Max retries exceeded')

            # If the command can be paginated, get a paginator and build the full result
            if client.can_paginate(command):
                paginator = client.get_paginator(command)
                result = paginator.paginate(**arguments).build_full_result()

            # Otherwise, execute the command directly
            else:
                result = getattr(client, command)(**arguments)

            # Break the loop if the command was executed successfully
            break

        # If a ClientError is raised, handle it
        except ClientError as e:
            # If the error is due to throttling, sleep for a while and then retry
            if e.response['Error']['Code'] == 'Throttling':
                from time import sleep
                sleep(2 * attempt)

            # If the error is due to any other reason, raise it
            else:
                raise e

    result = WalkableDict(result)

    # If a result key is specified, extract the result using the key
    if isinstance(result_path, str):
        result = result.walk(result_path)

    elif isinstance(result_path, (list, tuple)):
        result = {
            path: result.walk(path)
            for path in result_path
        }

    # Otherwise, extract the result using the first key that is not 'Marker' or 'NextToken'
    else:
        for key in result.keys():
            if key in ['Marker', 'NextToken']:
                continue

            else:
                result = WalkableDict(result[key])
                break

    return result
