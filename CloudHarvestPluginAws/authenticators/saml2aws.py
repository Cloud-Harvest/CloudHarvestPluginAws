from CloudHarvestCoreTasks.base import BaseAuthenticationTask
from CloudHarvestCorePluginManager.decorators import register_definition
from typing import List
from logging import getLogger
from concurrent.futures import ProcessPoolExecutor
from .functions import write_credentials

logger = getLogger('harvest')


@register_definition
class AwsSamlAuthenticatorTask(BaseAuthenticationTask):
    """
    This class is used to authenticate with AWS using SAML.

    Attributes:
        binary (str): The path to the saml2aws binary.
        config (str): The path to the saml2aws configuration file.
        username (str): The username for authentication.
        password (str): The password for authentication.
        output_path (str): The path where the AWS credentials will be written.
        roles (list): The list of roles for which the user can assume.
        max_workers (int): The maximum number of worker threads.
        pool (ProcessPoolExecutor): The process pool executor for parallel execution.
    """

    def __init__(self,
                 binary_file: str = None,
                 binary_config: str = None,
                 username: str = None,
                 password: str = None,
                 output_path: str = None,
                 max_workers: int = 2,
                 *args,
                 **kwargs):
        """
        Initialize the AwsSamlAuthenticatorTask.

        Args:
            binary_file (str): The path to the saml2aws binary.
            binary_config (str): The path to the saml2aws configuration file.
            username (str): The username for authentication.
            password (str): The password for authentication.
            output_path (str): The path where the AWS credentials will be written.
            max_workers (int): The maximum number of worker threads.
        """

        super().__init__(*args, **kwargs)

        self.username = username
        self.password = password
        self.output_path = output_path
        self.roles = []

        self.binary = binary_file or which_saml2aws()
        self.config = self._find_config((binary_config, ))

        self.max_workers = max_workers
        self.pool = ProcessPoolExecutor(max_workers=self.max_workers)

        self.results = []

        # init checks
        if not self.binary:
            raise ValueError('saml2aws is not installed. Please install it and try again.')

        if not self.config:
            raise ValueError('No configuration found. Please create a configuration file and try again.')

        if not all([self.username, self.password]):
            raise ValueError('Username and password are required for authentication.')

    def __enter__(self) -> 'AwsSamlAuthenticatorTask':
        """
        Enter context manager.
        """
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """
        Exit context manager.
        """
        del self.pool
        return None

    @staticmethod
    def _find_config(*args) -> str:
        """
        Locates the saml2aws configuration file from a list of possible directories.

        Args:
            args (tuple): The paths to the configuration files.

        Returns:
            str: The path to the first existing configuration file.
        """

        from os.path import join

        file_locations = [
            '~/.harvest/api/plugins/api-plugin-aws/saml2aws.config',
            '/etc/harvest.d/api/plugins/api-plugin-aws/saml2aws.config',
            f'{join(__file__, "..", "saml2aws.config")}',
        ]

        file_locations = args if args else [] + file_locations

        return get_first_file(*file_locations)

    def _list_roles(self) -> List[str]:
        """
        List the roles that the user can assume.

        Returns:
            list: The list of roles.
        """

        args = [
            self.binary,
            'list-roles',
            '--skip-prompt',
            '--username', self.username,
            '--password', self.password,
        ]

        roles = run_command(*args)
        return roles

    def _login(self) -> 'AwsSamlAuthenticatorTask':
        """
        Login to AWS and generate the tokens.
        """

        def _generate_tokens_worker_thread(role: str) -> dict:
            """
            This method is a worker thread that generates AWS tokens for a given role.

            It uses the saml2aws binary to login to AWS and generate the tokens. The tokens are then used to get the account name.

            Args:
                role (str): The AWS role for which to generate the tokens.

            Returns:
                dict: A dictionary containing the AWS tokens and account information.
            """

            # Prepare the arguments for the saml2aws login command
            args = [
                self.binary,
                'login',
                '--skip-prompt',
                '--username', self.username,
                '--password', self.password,
                '--role', role,
                '--config', self.config,
                '--credential-process',
                '--session-duration', str(3600)
            ]

            # Run the saml2aws login command and parse the output as JSON
            from json import loads
            saml2aws_output = loads('\n'.join(run_command(*args)))

            # Get the account name from the AWS tokens
            saml2aws_output['Account'] = account_name_from_token(access_key_id=saml2aws_output['AccessKeyId'],
                                                                 secret_access_key=saml2aws_output['SecretAccess'],
                                                                 session_token=saml2aws_output['SessionToken'])

            # Construct the profile name
            saml2aws_output['Profile'] = '-'.join([
                'aws',
                saml2aws_output['Account'],
                role.split('/')[-1].lower()
            ])

            from dateutil.parser import parse
            saml2aws_output['Expiration'] = parse(saml2aws_output['Expiration']).isoformat()

            return saml2aws_output

        # Map the roles to the ProcessPoolExecutor
        futures = self.pool.map(_generate_tokens_worker_thread, self._list_roles())

        # Wait for the threads to finish
        self.pool.shutdown(wait=True, cancel_futures=False)

        # Get the results from the processes
        login_results = list(futures)

        self.results = login_results

        return self

    def run(self) -> 'AwsSamlAuthenticatorTask':
        self._list_roles()
        self._login()

        if self.output_path:
            # Write the credentials to the output path
            write_credentials(self.results, self.output_path)

        return self


def get_first_file(*args) -> str or None:
    """
    Get the first file which exists from a list of paths.
    """

    from os.path import abspath, isfile, expanduser, exists

    for path in args:
        if path is not None:
            abs_path = abspath(expanduser(path))
            if exists(abs_path) and isfile(abs_path):
                logger.debug(f'Found file: {abs_path}')
                return abs_path


def run_command(*args) -> List[str]:
    """
    Run a command and return the output as a list of lines.
    """
    
    from subprocess import run, PIPE
    result = run(args=args, stdout=PIPE, stderr=PIPE, text=True)

    return result.stdout.splitlines() or result.stderr.splitlines()


def account_name_from_token(access_key_id: str,
                            secret_access_key: str,
                            session_token: str) -> str:
    """
    Get the account name from the account ID.
    """
    from boto3 import Session

    session = Session(aws_access_key_id=access_key_id,
                      aws_secret_access_key=secret_access_key,
                      aws_session_token=session_token)

    sts = session.client('sts')
    account_name = sts.get_caller_identity()['Account']

    return account_name


def which_saml2aws() -> str:
    from shutil import which
    return which('saml2aws')
