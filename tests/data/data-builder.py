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

    for _service in services.keys():
        for _type in services[_service].keys():
            print(f'{_service}.{_type}')

            service_type = services[_service][_type]

            c = (' '.join([
                aws_binary,
                _service,
                service_type['command'],
                '--region us-east-1',
                '--generate-cli-skeleton output'
            ]))

            print(c)

            process = Popen(args=c.split(' '),
                            stdout=PIPE)

            p = process.communicate()

            template = loads(p[0].decode('utf8'))

            result_key = [k for k in template.keys() if k != 'Marker'][0]

            with open(f'./skeletons/{_service}.{_type}.json', 'w') as skeleton_stream:
                from pprint import pformat
                skeleton_stream.write(pformat(template[result_key]))

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

            with open(f'./outputs/{_service}.{_type}.json', 'w') as output_stream:
                output_stream.write(pformat(results))
                output_stream.write('\n')


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
