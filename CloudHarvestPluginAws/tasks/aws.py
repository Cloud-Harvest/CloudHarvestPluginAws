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
                 result_path: str = None,
                 list_result_as_key: str = None,
                 max_retries: int = 10,
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
            result_path (str, optional): Path to the results. When not provided, the path is the first key that is not 'Marker' or 'NextToken'.
            list_result_as_key (str, optional): Converts a list result into a dictionary whose key is the value of this argument for each item.
            max_retries (int, optional): The maximum number of retries for the command. Defaults to 10.
        """
        # Initialize parent class
        super().__init__(*args, **kwargs)

        # Set STAR: Service, Type, Account, Region
        self.service = service or self.task_chain.variables.get('service')
        self.type = type or self.task_chain.variables.get('type')
        self.account = account or self.task_chain.variables.get('account')
        self.region = region or self.task_chain.variables.get('region')

        # boto3 session and client inputs
        from CloudHarvestCoreTasks.environment import Environment
        self.role = role or Environment.get(name='env.platforms.aws.role_name')
        self.command = command
        self.arguments = arguments or {}
        self.max_retries = max_retries

        # Output manipulation
        self.result_path = result_path
        self.list_result_as_key = list_result_as_key

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

        from CloudHarvestPluginAws.credentials import CachedProfiles, get_credentials

        # Import the Session class from boto3
        from boto3 import Session

        # Create a new session with either the `{profile_name: 'profile_name'}` (for credentials already provisioned) or
        # `{access_key: 'aws_access_key_id', aws_secret_access_key, 'aws_session_token'}` (for temporary credentials)
        session = Session(**get_credentials(account_number=self.account, role_name=self.role))

        # Set the account_alias attribute
        self.account_alias = CachedProfiles.profiles[self.account]['account_alias']

        # Create a client for the specified service in the specified region
        client = session.client(service_name=self.service, region_name=self.region)

        # Initialize the result and attempt counter
        attempt = 0

        # Make sure the command exists in the client before making any attempts
        if not hasattr(client, self.command):
            raise Exception(f'Command `{self.command}` not found in service `{self.service}`')

        # Start a loop to execute the command
        while True:
            # Increment the attempt counter
            attempt += 1

            try:
                # If the maximum number of retries is exceeded, raise an exception
                if attempt > self.max_retries:
                    raise Exception('Max retries exceeded')

                # If the command can be paginated, get a paginator and build the full result
                if client.can_paginate(self.command):
                    paginator = client.get_paginator(self.command)
                    result = paginator.paginate(**self.arguments).build_full_result()

                # Otherwise, execute the command directly
                else:
                    result = getattr(client, self.command)(**self.arguments)

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
                    raise e.args

        # If a result key is specified, extract the result using the key
        if self.result_path:
            from CloudHarvestCoreTasks.dataset import WalkableDict
            result = WalkableDict(result).walk(self.result_path)

        # Otherwise, extract the result using the first key that is not 'Marker' or 'NextToken'
        else:
            for key in result.keys():
                if key in ['Marker', 'NextToken']:
                    continue

                else:
                    result = result[key]
                    break

        # If a list result as key is specified and the result is a list, transform the result
        if self.list_result_as_key and isinstance(result, list):
            result = [
                {
                    self.list_result_as_key: r
                }
                for r in result
            ]

        # Add starting metadata to the result
        if isinstance(result, list):
            for record in result:
                record['Harvest']['AccountId'] = self.account
                record['Harvest']['AccountName'] = self.account_alias

        elif isinstance(result, dict):
            result['Harvest'] = {
                'AccountId': self.account,
                'AccountName': self.account_alias
            }

        # Store the result
        self.result = result

        # Return the instance of the AwsTask
        return self
