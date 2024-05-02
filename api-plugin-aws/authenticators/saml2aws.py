# from core.tasks import BaseTask
from typing import List
from logging import getLogger
from concurrent.futures import ProcessPoolExecutor

logger = getLogger('harvest')


class AwsSamlAuthenticator:
    def __init__(self,
                 binary_file: str = None,
                 binary_config: str = None,
                 username: str = None,
                 password: str = None,
                 output_path: str = '~/.aws/credentials',
                 max_workers: int = 2,
                 *args,
                 **kwargs):

        super().__init__(*args, **kwargs)

        self.username = username
        self.password = password
        self.output_path = output_path
        self.roles = []

        self.binary = binary_file or which_saml2aws()
        self.config = self._load_config(binary_config)

        self.max_workers = max_workers
        self.pool = ProcessPoolExecutor(max_workers=self.max_workers)

        # init checks
        if not self.binary:
            raise ValueError('saml2aws is not installed. Please install it and try again.')

        if not self.config:
            raise ValueError('No configuration found. Please create a configuration file and try again.')

        if not all([self.username, self.password]):
            raise ValueError('Username and password are required for authentication.')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    @staticmethod
    def _load_config(*args) -> str:
        from os.path import join

        file_locations = [
            '~/.harvest/api/plugins/api-plugin-aws/saml2aws.conf',
            '/etc/harvest.d/api/plugins/api-plugin-aws/saml2aws.conf',
            f'{join(__file__, "..", "saml2aws.conf")}',
        ]

        file_locations = args if args else [] + file_locations

        return get_first_file(*file_locations)

    def list_roles(self):
        args = [
            self.binary,
            'list-roles',
            '--skip-prompt',
        ]

        roles = run_command(*args)
        return roles

    def login(self, *args, **kwargs):
        def _generate_tokens_worker_thread(role: str) -> dict:
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

            from json import loads
            saml2aws_output = loads('\n'.join(run_command(*args)))

            saml2aws_output['Account'] = account_name_from_token(access_key_id=saml2aws_output['AccessKeyId'],
                                                                 secret_access_key=saml2aws_output['SecretAccess'],
                                                                 session_token=saml2aws_output['SessionToken'])

            saml2aws_output['Profile'] = '-'.join([
                'aws',
                saml2aws_output['Account'],
                role.split('/')[-1].lower()
            ])

            return saml2aws_output

        futures = self.pool.map(_generate_tokens_worker_thread, self.list_roles())

        self.pool.shutdown(wait=True, cancel_futures=False)

        login_results = list(futures)

        self.write_credentials(login_results=login_results)

    def write_credentials(self, login_results: List[dict]):
        from configparser import ConfigParser

        config = ConfigParser()

        for result in login_results:
            profile = result['Profile']

            config[profile] = {
                'aws_access_key_id': result['AccessKeyId'],
                'aws_secret_access_key': result['SecretAccess'],
                'aws_session_token': result['SessionToken'],
                'expiration': result['Expiration'],
            }

        with open(self.output_path, 'w') as configfile:
            config.write(configfile)

        logger.debug(f'Wrote {len(login_results)} credentials to {self.output_path}')


def get_first_file(*args) -> str:
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
