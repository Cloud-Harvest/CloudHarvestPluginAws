from CloudHarvestCoreTasks.tasks import BaseTask
from CloudHarvestCorePluginManager.decorators import register_definition
from botocore.exceptions import ClientError


@register_definition(name='aws', category='task')
class AwsTask(BaseTask):
    """
    AwsTask is a class for managing AWS tasks. It provides a way to interact with AWS services using boto3.

    Attributes:
        credentials (str): The AWS profile_name to use for the session.
        region (str): The AWS region to use for the session.
        service (str): The AWS service to interact with.
        command (str): The command to execute on the AWS service.
        arguments (dict): The arguments to pass to the command.
        result_key (str, optional): The key to use to extract the result from the response. If a period-delimited key is
                                    provided, the function get_nested_values will be used to extract the desired subkey.
                                    When not provided, the first key that is not 'Marker' or 'NextToken' will be used.
        list_result_as_key (str, optional): When the result is a list, each list item will be transformed into a
                                            dictionary with this key.
        max_retries (int, optional): The maximum number of retries for the command. Defaults to 10.
        result: The result of the command execution.

    Methods:
        run(): Executes the command on the AWS service and stores the result.
    """

    def __init__(self,
                 credentials: dict,
                 region: str or None,
                 service: str,
                 command: str,
                 arguments: dict,
                 result_key: str = None,
                 list_result_as_key: str = None,
                 max_retries: int = 10,
                 *args,
                 **kwargs):
        """
        Constructs all the necessary attributes for the AwsTask object.

        Args:
            profile (dict): Either the `{profile_name: 'profile_name'}` or `{access_key: 'aws_access_key_id', aws_secret_access_key, 'aws_session_token'}`.
            region (str): The AWS region to use for the session. Sometimes None when the service does not require a region.
            service (str): The AWS service to interact with.
            command (str): The command to execute on the AWS service.
            arguments (dict): The arguments to pass to the command.
            result_key (str, optional): The key to use to extract the result from the response.
            list_result_as_key (str, optional): The key to use to list the result if the result is a list.
            max_retries (int, optional): The maximum number of retries for the command. Defaults to 10.
        """
        # Initialize parent class
        super().__init__(*args, **kwargs)

        # Set the AWS profile_name, region, service, command, and arguments
        self.credentials = credentials
        self.region = region
        self.service = service
        self.command = command
        self.arguments = arguments or {}

        # Set the result key, list result as key, and max retries
        self.result_key = result_key
        self.list_result_as_key = list_result_as_key
        self.max_retries = max_retries

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
        # Import the Session class from boto3
        from boto3 import Session

        # Create a new session with either the `{profile_name: 'profile_name'}` (for credentials already provisioned) or
        # `{access_key: 'aws_access_key_id', aws_secret_access_key, 'aws_session_token'}` (for temporary credentials)
        session = Session(**self.credentials)

        # Create a client for the specified service in the specified region
        client = session.client(service_name=self.service, region_name=self.region)

        # Initialize the result and attempt counter
        result = None
        attempt = 0

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
                    raise

            # After the try/except block, check if a result was returned
            finally:
                if result is None:
                    raise Exception('No result returned')

        # If a result key is specified, extract the result using the key
        if self.result_key:
            from CloudHarvestCoreTasks.helpers import get_nested_values
            result = get_nested_values(self.result_key, result)

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

        # Store the result
        self.data = result

        # Return the instance of the AwsTask
        return self
