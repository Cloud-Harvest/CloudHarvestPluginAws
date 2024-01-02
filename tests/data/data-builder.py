#!/bin/env python

from subprocess import Popen, PIPE

_invalid_result_keys = [str(s).lower() for s in ('Marker', 'NextToken')]
_data_gathering_command_prefixes = ('describe', 'get', 'list')


def main(aws: str, count: int, max_workers: int, no_cache: bool):
    """
    Converts API calls into test records and prints them to stdout.
    :param aws: path to the aws cli tool
    :param count: the number of test records to create per service/type
    :param max_workers: maximum number of threads to run when creating test records
    :param no_cache: do not use cached service, command, or template information; retrieve new directives from the aws cli
    :return: outputs a JSON file to the screen
    """
    from datetime import datetime, timezone

    start_time = datetime.now(tz=timezone.utc).timestamp()

    from os.path import exists
    from os import mkdir
    if not exists('./cache'):
        mkdir('./cache')

    from concurrent.futures import ThreadPoolExecutor, wait, ALL_COMPLETED
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(get_commands, service, no_cache) for service in get_services(no_cache=no_cache)]

        wait(futures, return_when=ALL_COMPLETED)

    commands = []
    [commands.extend(f.result()) for f in futures]

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = [pool.submit(get_outputs, aws, service_command, count, no_cache)
                   for service_command in commands
                   if any([service_command.split('.')[1].lower().startswith(s)
                           for s in _data_gathering_command_prefixes])]

        wait(futures, return_when=ALL_COMPLETED)

    # results = {f.result()[0]: f.result()[1] for f in futures}

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
            print(f'loaded: {commands_cache_file}')

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
                print(service_command)

                if any([command.startswith(s) for s in _data_gathering_command_prefixes]):
                    result.append(service_command)

        with open(commands_cache_file, 'w') as commands_cache:
            commands_cache.write(dumps(result, default=str, indent=4))
            commands_cache.write('\n')

    return result


def get_outputs(aws: str, service_command: str, count: int, no_cache: bool) -> tuple:
    service, command = service_command.split('.', maxsplit=1)
    from datetime import datetime, timezone

    start_time = datetime.now(tz=timezone.utc).timestamp()

    from json import dumps, loads
    from os.path import exists

    command_output_file = f'./cache/{service}.{command}.output.json'
    random_output_file = f'./cache/{service}.{command}.random.json'

    if exists(command_output_file) and no_cache is False:
        with open(command_output_file, 'r') as command_output_stream:
            print(f'{service_command}: skipped (cached): {command_output_file}')
            return loads(command_output_stream.read())

    else:
        from json import loads
        from hashlib import md5

        def run_command(*args) -> tuple:
            required = []
            while True:
                r = [f'{r}=""' for r in required]
                c = ' '.join([*args, *r])

                process = Popen(args=[*args, *r], stdout=PIPE, stderr=PIPE)
                output_raw = process.communicate()[0]

                # RETRY: this command requires an input of some kind
                if b'aws: error: the following arguments are required:' in output_raw:
                    from re import findall
                    required = findall(b'--.*\\w', output_raw)
                    print(f'{c}: WARN: added: {required}')
                    continue

                # ERROR: this command won't give us back a skeleton
                elif b'Unknown options: --generate-cli-skeleton' in output_raw:
                    print(f'{c}: ERROR: --generate-cli-skeleton not supported')
                    break

                # hopefully the output we want
                else:
                    return output_raw, required

        input_raw, input_required = run_command(aws, service, command,
                                                '--region=us-east-1', '--generate-cli-skeleton')

        output_raw, output_required = run_command(aws, service, command,
                                                  '--region=us-east-1', '--generate-cli-skeleton', 'output')

        output_json = loads(output_raw.decode('utf8'))

        result_key = [k for k in output_json.keys() if k.lower() not in _invalid_result_keys]
        result_key = result_key[0] if len(result_key) > 0 else None

        boto_command = command.replace('-', '_')
        from boto3 import Session
        session = Session(region_name='us-east-1')
        has_command = hasattr(session.client(service_name=service), boto_command)

        result = {}

        try:
            result = {
                'input': {
                    'template': loads(input_raw.decode('utf8')),
                    'required': input_required,
                    'md5': md5(input_raw).hexdigest(),
                    'boto_command': boto_command,
                    'boto_command_matches': has_command
                },
                'output': {
                    'template': output_json.get(result_key),
                    'required': output_required,
                    'md5': md5(output_raw).hexdigest(),
                    'randomized': create_random_data(template=output_json[result_key], count=count) if result_key else [],
                    'result_key': result_key
                },
                'meta': {
                    'start': start_time,
                    'end': datetime.now(tz=timezone.utc).timestamp(),
                    'duration': datetime.now(tz=timezone.utc).timestamp() - start_time
                }
            }

            with open(command_output_file, 'w') as command_output_stream:
                command_output_stream.write(dumps(result, default=str, indent=4))
                command_output_stream.write('\n')

            with open(random_output_file, 'w') as random_output_stream:
                random_output_stream.write(dumps(result['output']['randomized'], default=str, indent=4))
                random_output_stream.write('\n')

        except Exception as ex:
            print(f'{service_command}: ERROR: ' + ' '.join(ex.args))

        finally:
            print(f'{service_command}: '
                  f'{"WARN" if any([len(input_raw) == 0, 
                                    len(output_raw) == 0,
                                    result_key is None]) else "INFO"}: ' + \
                  ' | '.join(
                [
                    str(len(input_raw)),
                    str(len(output_raw)),
                    result_key,
                    f'done in {result["meta"]["duration"]} seconds -> {command_output_file}'
                ])
            )

        return service_command, result


def create_random_data(template: dict, count: int) -> list:
    result = []

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

        unflatten = unflatten_list(r, separator='.')['result']

        if isinstance(unflatten, list):
            result.extend(unflatten)

        else:
            result.append(unflatten)

    return result


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-c', '--count', default=10,
                        help='Number of test records to create per service. (default: 10)')
    parser.add_argument('-w', '--max-workers', default=16, type=int,
                        help='Number of data generation threads to run at once. (default: 16)')
    parser.add_argument('--no-cache', action='store_true', help='do not use the services or command cache')

    arguments = vars(parser.parse_args())

    from os.path import expanduser
    from os import environ
    from shutil import which
    aws_binary = expanduser(which('aws', path=environ.get('PATH')))

    main(aws=aws_binary, **arguments)
