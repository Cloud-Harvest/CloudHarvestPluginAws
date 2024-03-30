#!/bin/env python

from subprocess import Popen, PIPE
from typing import List

_invalid_result_keys = [str(s).lower() for s in ('Marker', 'NextToken')]
_data_gathering_command_prefixes = ('describe', 'get', 'list')

_dummy_account_names = ['account1', 'account2', 'account3', 'account4', 'account5']
_dummy_account_ids = ['123456789012', '234567890123', '345678901234', '456789012345', '567890123456']
_dummy_region_names = ['us-east-1', 'us-west-2', 'eu-west-1', 'eu-central-1', 'ap-southeast-1']


def main(aws: str, count: int, max_workers: int, no_cache: bool, services: List[str] = []):
    """
    Converts API calls into test records and prints them to stdout.
    :param services: AWS services to generate test records for
    :param aws: path to the aws cli tool
    :param count: the number of test records to create per service/type
    :param max_workers: maximum number of threads to run when creating test records
    :param no_cache: do not use cached service, command, or template information; retrieve new directives from the aws cli
    :return: outputs a JSON file to the screen
    """
    from datetime import datetime, timezone

    start_time = datetime.now(tz=timezone.utc).timestamp()
    print('starting...')

    from os.path import exists
    from os import mkdir
    if not exists('./cache'):
        mkdir('./cache')

    from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(get_commands, service, no_cache) for service in services or get_services(no_cache=no_cache)]
        print(f'generating commands for {len(futures)} services...')
        wait(futures, return_when=ALL_COMPLETED)

    commands = []
    [commands.extend(f.result()) for f in futures]

    print('starting processes...')
    from concurrent.futures import ProcessPoolExecutor
    with ProcessPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(get_outputs, aws, service_command, count, no_cache)
                   for service_command in commands
                   if any([service_command.split('.')[1].lower().startswith(s)
                           for s in _data_gathering_command_prefixes])]

        from rich.progress import Progress, BarColumn, TimeElapsedColumn, TimeRemainingColumn, SpinnerColumn
        config = (
            SpinnerColumn(),
            "[progress.description]{task.description}",
            BarColumn(),
            "[progress.percentage]{task.percentage:3.0f}%",
            TimeElapsedColumn(),
            "/",
            TimeRemainingColumn(),
            "[progress.completed]{task.completed}/[progress.total]{task.total}"
        )

        with Progress(*config) as progress:
            task = progress.add_task('Data Harvest', total=len(futures))

            while True:
                from time import sleep
                completed = len([f for f in futures if f.done()])
                progress.update(task, completed=completed)
                if completed == len(futures):
                    break

                else:
                    sleep(1)

    end_time = datetime.now(tz=timezone.utc).timestamp()

    print(f'done in {end_time - start_time} seconds')

    return


def get_services(no_cache: bool) -> list:
    from os.path import exists
    from json import loads, dumps

    services_file = './cache/services.json'
    if exists(services_file) and no_cache is False:
        with open(services_file, 'r') as services_cache:
            services = loads(services_cache.read())
            print(f'loaded: {services_file}')

    else:
        process = Popen(args=['aws', 'help'], stdout=PIPE)
        process = process.communicate()[0].decode('utf8').split('\n')

        services = []
        read_services = False
        for r in process:
            row = r.strip()

            if 'AVAILABLE SERVICES' in row:
                read_services = True

            elif read_services is True and row != '':
                if 'SEE ALSO' in row:
                    break

                else:
                    service = row.split(' ')[-1]
                    services.append(service)

        with open('./cache/services.json', 'w') as services_cache:
            services_cache.write(dumps(services, default=str, indent=4))
            services_cache.write('\n')

    return services


def get_commands(service: str, no_cache: bool) -> list:
    from os.path import exists
    from json import dumps, loads

    commands_cache_file = f'./cache/{service}.commands.json'

    if exists(commands_cache_file) and no_cache is False:
        with open(commands_cache_file, 'r') as commands_cache:
            result = loads(commands_cache.read())
            # print(f'loaded: {commands_cache_file}')

    else:
        from subprocess import Popen, PIPE
        process = Popen(args=['aws', service, 'help'], stdout=PIPE)
        process = process.communicate()[0].decode('utf8').split('\n')

        result = []

        read_commands = False
        for row in process:

            if 'AVAILABLE COMMANDS' in row:
                read_commands = True

            elif read_commands is True and row != '' and not row.endswith('()'):
                command = row.split(' ')[-1]
                service_command = f'{service}.{command}'
                # print(service_command)

                if any([command.startswith(s) for s in _data_gathering_command_prefixes]):
                    result.append(service_command)

        with open(commands_cache_file, 'w') as commands_cache:
            commands_cache.write(dumps(result, default=str, indent=4))
            commands_cache.write('\n')

    return result


def get_outputs(aws: str, service_command: str, count: int, no_cache: bool) -> tuple:
    def safe_loads(s: (bytes, str)) -> dict:
        try:
            if isinstance(s, bytes):
                return loads(s.decode('utf8'))

            elif isinstance(s, str):
                return loads(s)

        except Exception as ex:
            return {'error': ex.args, 'raw': s.decode('utf8')}

    service, command = service_command.split('.', maxsplit=1)
    from datetime import datetime, timezone

    start_time = datetime.now(tz=timezone.utc).timestamp()

    from json import dumps, loads
    from os.path import exists

    command_output_file = f'./cache/{service}.{command}.output.json'
    random_output_file = f'./cache/{service}.{command}.random.json'

    if all([exists(command_output_file), exists(random_output_file)]) and no_cache is False:
        with open(command_output_file, 'r') as command_output_stream:
            # print(f'{service_command}: skipped (cached): {command_output_file}')
            return loads(command_output_stream.read())

    else:
        from json import loads

        def run_command(*args) -> tuple:
            def build_required_parameters(r: str) -> str:
                if any([True for s in ('count', 'hours', 'minutes', 'seconds') if r in s]):
                    param_result = f'{r}=1'

                elif 'arn' in r.lower():
                    param_result = f'{r}=arn:aws:{service}:us-west-2:111122223333:dummy/dummy/dummy'

                else:
                    param_result = f'{r}=dummy'

                return param_result

            required = []
            i = 0
            while True:
                i += 1
                req_args = [
                    build_required_parameters(r) for r in required
                ]

                merged_args = args + tuple(req_args)
                c = ' '.join(merged_args)

                process = Popen(args=merged_args, stdout=PIPE, stderr=PIPE)
                output_raw = b'\n'.join(process.communicate())

                if i >= 10:
                    print(f'{c}: ERROR: too many retries')
                    return b'', []

                # RETRY: this command requires an input of some kind
                if b'aws: error: the following arguments are required:' in output_raw:
                    from re import findall
                    required = [bytes(s).decode('utf8') for s in findall(b'--.*\\w', output_raw)]
                    if required:
                        required = [s.strip() for s in required[0].split(',')]

                    # print(f'{c}: WARN: added: {required}')
                    continue

                # ERROR: this command won't give us back a skeleton
                elif b'Unknown options: --generate-cli-skeleton' in output_raw:
                    print(f'{c}: ERROR: --generate-cli-skeleton not supported')
                    break

                # hopefully the output we want
                else:
                    return output_raw, required

        input_raw, input_required = run_command(aws, service, command, '--region=us-east-1', '--generate-cli-skeleton')
        output_raw, output_required = run_command(aws, service, command, '--region=us-east-1', '--generate-cli-skeleton', 'output')
        synopsis_raw, _ = run_command(aws, service, command, 'help')

        input_template = safe_loads(input_raw)
        output_json = safe_loads(output_raw)

        result_key = [k for k in output_json.keys() if k.lower() not in _invalid_result_keys]
        result_key = result_key[0] if len(result_key) > 0 else None
        possible_output_filter_key = [
            k for k in list(input_template.keys())
            if k not in ('Filters', 'MaxRecords', 'Marker')
        ]
        possible_output_filter_key = possible_output_filter_key[0] if len(possible_output_filter_key) > 0 else ['']

        synopsis = synopsis_raw.decode('utf8').split('\n')
        template_required = []

        synopsis_found = False
        template_required_inputs = []
        for line in synopsis:
            if 'SYNOPSIS' in line:
                synopsis_found = True

            if synopsis_found:
                if line.strip().startswith('--'):
                    template_required.append(line.strip().split(' ')[0].replace('-', ''))
                    template_required_inputs = [k for k in input_template.keys() if k.lower() in template_required]

                elif len(line.strip()) == 0:
                    break

        boto_command = command.replace('-', '_')
        from boto3 import Session
        session = Session(region_name='us-east-1')

        result = {}

        try:
            result = {
                'input': {
                    'template': input_template,
                    'template_required_inputs': template_required_inputs,
                    'required_cli_fields': input_required,
                    'boto_command': boto_command if hasattr(session.client(service_name=service), boto_command) else 'unknown',
                },
                'output': {
                    'template': {} if result_key == 'error' else output_json.get(result_key),
                    'required': output_required,
                    'result_key': result_key,
                    'possible_filter_key': possible_output_filter_key,
                },
                'meta': {
                    'service': service,
                    'type': type_from_command(command)
                }
            }

            with open(command_output_file, 'w') as command_output_stream:
                command_output_stream.write(dumps(result, default=str, indent=4))
                command_output_stream.write('\n')

            with open(random_output_file, 'w') as random_output_stream:
                if result_key == 'error':
                    random_data = output_json

                else:
                    random_data = create_random_data(template=output_json[result_key],
                                                     count=count,
                                                     primary_template_identifier=possible_output_filter_key or input_template.get('primary_template_identifier'),
                                                     service=service,
                                                     service_type=type_from_command(command)) if result_key != 'error' else []

                random_output_stream.write(dumps(random_data, default=str, indent=4))
                random_output_stream.write('\n')

        except Exception as ex:
            from traceback import format_exc
            print(f'{service_command}: ERROR: ' + ' '.join(ex.args) + '\n' + format_exc())

        finally:
            pass
            # print(f'{service_command}: '
            #       f'{"WARN" if any([len(input_raw) == 0,
            #                         len(output_raw) == 0,
            #                         result_key is None]) else "INFO"}: ' + \
            #       ' | '.join(
            #     [
            #         str(len(input_raw)),
            #         str(len(output_raw)),
            #         result_key,
            #         f'done in {result["meta"]["duration"]} seconds -> {command_output_file}'
            #     ])
            # )

        return service_command, result


def create_random_data(template: dict, count: int, service: str, service_type: str, primary_template_identifier: str = None) -> list:
    result = []

    if not isinstance(template, (dict, list)):
        return [{}]

    import random
    import string

    letters = string.ascii_lowercase

    from flatten_json import flatten, unflatten_list
    # place in {'result': template} because all flatten/unflatten_list inputs must be of the dict type
    flat_template = flatten({'result': template}, separator='.')

    for i in range(count):
        r = {}
        for k, v in flat_template.items():
            if isinstance(v, str):
                r[k] = ''.join(random.choice(letters) for i in range(16))

            else:
                r[k] = v

        metadata = flatten(create_metadata(service=service,
                                           type=service_type,
                                           filter_criteria=[] if primary_template_identifier is None else [
                                               primary_template_identifier
                                           ]),
                           separator='.')

        r.update({f'result.0.Harvest.{k}': v for k, v in metadata.items()})

        # remove this top level object which breaks the unflatten process
        for key in ['result', 'result.0']:
            if r.get(key):
                r.pop(key)

        try:
            unflatten = unflatten_list(r, separator='.')['result']

        except Exception as ex:
            print(f'ERROR: {ex.args}')
            from pprint import pprint
            pprint(r)
            return [{}]

        if isinstance(unflatten, list):
            result.extend(unflatten)

        else:
            result.append(unflatten)

    return result


def type_from_command(command: str) -> str:
    for prefix in ['list', 'describe']:
        if command.startswith(prefix):
            return command[len(prefix) + 1:].replace('-', '_')


def create_metadata(service: str, type: str, account: str = None, region: str = None, filter_criteria: List[str] = None) -> dict:
    def random_bool():
        from random import choice
        return choice([True, False])

    def random_date():
        from datetime import datetime
        from random import randint
        now_timestamp = int(datetime.now().timestamp())
        six_months_ago = int(now_timestamp - (60 * 60 * 24 * 30 * 6))
        return datetime.fromtimestamp(randint(six_months_ago, now_timestamp))

    with open('../../version', 'r') as version_file:
        version = version_file.read().strip()

    result = {}
    try:
        import random

        result = {
            'Platform': 'aws',
            'Service': service,
            'Type': type,
            'Account': account or random.choice(_dummy_account_names),
            'Region': region or random.choice(_dummy_region_names),
            'Module': {
                # Always include the account and geographic region here
                'FilterCriteria': ['Harvest.Account', 'Harvest.Region'] + [f for f in filter_criteria],
                'Name': 'harvest-client-cli',
                'Repository': 'https://github.com/Cloud-Harvest/client-cli',
                'Version': version
            },
            'Dates': {
                'DeactivatedOn': '',
                'LastSeen': random_date()
            },
            'Active': random_bool()
        }
    except Exception as ex:
        print(f'ERROR: {service}.{type}: {ex.args}')

    finally:
        return result


if __name__ == '__main__':
    from argparse import ArgumentParser
    from rich_argparse import RawTextRichHelpFormatter

    parser = ArgumentParser(formatter_class=RawTextRichHelpFormatter)
    parser.add_argument('-c', '--count', default=10,
                        help='Number of test records to create per service. (default: 10)')
    parser.add_argument('-w', '--max-workers', default=16, type=int,
                        help='Number of data generation threads to run at once. (default: 16)')
    parser.add_argument('--no-cache', action='store_true', help='do not use the services or command cache')
    parser.add_argument('--services', nargs='+', default=[], help='services to generate test data for, defaults to all')

    arguments = vars(parser.parse_args())

    from os.path import expanduser
    from os import environ
    from shutil import which
    aws_binary = expanduser(which('aws', path=environ.get('PATH')))

    main(aws=aws_binary, **arguments)

