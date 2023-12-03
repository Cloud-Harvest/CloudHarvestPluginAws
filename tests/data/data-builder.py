#!/bin/env python

def main(services_file: str, count: int, max_workers: int):
    """
    Converts API calls into test records and prints them to stdout.
    :param services_file: YAML file containing the services and their respective api calls/depths
    :param count: the number of test records to create per service/type
    :param max_workers: maximum number of threads to run when creating test records
    :return: outputs a JSON file to the screen
    """

    with open(services_file, 'r') as services_stream:
        from yaml import load, FullLoader
        services = load(services_stream, Loader=FullLoader)

    from flatten_json import flatten, unflatten_list
    from json import loads
    from os.path import expanduser
    from os import environ
    from shutil import which
    from subprocess import Popen, PIPE

    aws_binary = expanduser(which('aws', path=environ.get('PATH')))

    z = 0
    s = len(set(['.'.join(f.split('.')[0:2])
                 for f in flatten(services, separator='.')]))

    for _service in services.keys():
        for _type in services[_service].keys():
            z += 1
            print(f'\nbuild: {_service}.{_type}: {z} / {s}')

            service_type = services[_service][_type]

            c = (' '.join([
                aws_binary,
                _service,
                service_type['command'],
                '--region us-east-1',
                '--generate-cli-skeleton output'
            ]))

            print(f'cmd  : {c}')

            process = Popen(args=c.split(' '),
                            stdout=PIPE)

            p = process.communicate()

            template = loads(p[0].decode('utf8'))

            result_key = [k for k in template.keys() if k != 'Marker'][0]

            skeleton_file = f'./skeletons/{_service}.{_type}.json'

            import hashlib
            from os.path import exists
            if exists(skeleton_file):
                old_skeleton_md5 = hashlib.md5(open(skeleton_file, 'rb').read()).hexdigest()

            else:
                old_skeleton_md5 = None

            with open(skeleton_file, 'w') as skeleton_stream:
                from pprint import pformat
                skeleton_stream.write(pformat(template[result_key]))
                skeleton_stream.write('\n')
                print(f'wrote: {skeleton_file}')

            if old_skeleton_md5 is not None:
                new_skeleton_md5 = hashlib.md5(open(skeleton_file, 'rb').read()).hexdigest()

                if new_skeleton_md5 != old_skeleton_md5:
                    print(f'WARNING: {_service}.{_type} md5 do not match: {skeleton_file}: {old_skeleton_md5} / {new_skeleton_md5}')

            if isinstance(template[result_key], list):
                flat_template = flatten(template[result_key][0], separator='.')

            else:
                flat_template = flatten(template[result_key], separator='.')

            import random
            import string
            from copy import deepcopy
            results = []

            for x in range(0, count):
                dc_template = deepcopy(flat_template)
                for key, value in dc_template.items():
                    if isinstance(value, str):
                        letters = string.ascii_lowercase
                        dc_template[key] = ''.join(random.choice(letters) for i in range(10))

                results.append(unflatten_list(dc_template, separator='.'))

            output_file = f'./outputs/{_service}.{_type}.json'
            with open(output_file, 'w') as output_stream:
                output_stream.writelines([pformat(o) + '\n' for o in results])

            print(f'wrote: {output_file}')


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-f', '--services-file', default='./services.yaml',
                        help='Location of the services.yaml')
    parser.add_argument('-c', '--count', default=50,
                        help='Number of test records to create per service.')
    parser.add_argument('-w', '--max-workers', default=10, type=int,
                        help='Number of data generation threads to run at once.')

    args = vars(parser.parse_args())
    main(**args)
