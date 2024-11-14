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

    def on_complete(self) -> 'BaseTask':
        """
        This method is called when the task is completed. It returns the instance of the task.

        Returns:
            BaseTask: Returns the instance of the task.
        """

        # Call the parent class on_complete() to set status and runtime completion
        super().on_complete()

        return self

# def get_nested_values(s: str, d: dict):
#     """
#     This function takes a string `s` and a dictionary `d` as inputs. The string `s` represents a sequence of keys
#     separated by periods, and the dictionary `d` is a nested structure of dictionaries and lists. The function walks
#     through the dictionary `d` following the sequence of keys in `s`, and returns a list of all values that match the
#     key path specified by `s`. If `s` specifies a path that includes a list, the function will return values from all
#     items in the list.
#
#     This function was developed with the intention of addressing the following use case:
#         - EC2 describe_db_instances returns a Reservations (list) with Groups (list) and Instances (list)
#         - For the purposes of retreiving just Instances of Groups, the function can be used to extract either key
#
#         >>> {
#         >>>     "Reservations": [
#         >>>         {
#         >>>             "Groups": [
#         >>>                 {
#         >>>                     "GroupName": "string",
#         >>>                     "GroupId": "string"
#         >>>                 }
#         >>>             ],
#         >>>             "Instances": [
#         >>>                 {
#         >>>                     "AmiLaunchIndex": 123,
#         >>>                     "ImageId": "string",
#         >>>                     "InstanceId": "string"
#         >>>                 }
#         >>>             ]
#         >>>         }
#         >>>     ],
#         >>>     "NextToken": "string"
#         >>> }
#
#     Args:
#         s (str): A string representing a sequence of keys separated by periods.
#         d (dict): A dictionary with a nested structure of dictionaries and lists.
#
#     Returns:
#         list: A list of all values that match the key path specified by `s`.
#     """
#
#     # Split the input string `s` by periods to get a list of keys
#     keys = s.split('.')
#
#     # Initialize an empty list `results` to store the final results
#     results = []
#
#     def walk_dict(d, keys):
#         """
#         This is a helper function that walks through the dictionary `d` following the sequence of keys.
#
#         Args:
#             d (dict or list): A dictionary or list to walk through.
#             keys (list): A list of keys to follow.
#         """
#
#         # If `keys` is empty, append `d` to `results`
#         if not keys:
#             if isinstance(d, list):
#                 results.extend(d)
#
#             else:
#                 results.append(d)
#
#         else:
#             # Get the first key and the rest of the keys
#             first_key, rest_keys = keys[0], keys[1:]
#
#             # If `d` is a dictionary and the first key is in `d`, call `walk_dict` with `d[first_key]` and the rest of the keys
#             if isinstance(d, dict) and first_key in d:
#                 walk_dict(d[first_key], rest_keys)
#
#             # If `d` is a list, iterate over its elements. For each element, call `walk_dict` with the element and `keys`
#             elif isinstance(d, list):
#                 for item in d:
#                     walk_dict(item, keys)
#
#     # Call `walk_dict` with the input dictionary `d` and the list of keys
#     walk_dict(d, keys)
#
#     # Return `results`
#     return results
