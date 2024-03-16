#!/bin/env python
import boto3


def map_aws_services() -> list:
    services = session.get_available_services()

    from concurrent.futures import ThreadPoolExecutor
    pool = ThreadPoolExecutor(max_workers=16)

    futures = [pool.submit(map_aws_service, service) for service in services]

    pool.shutdown(wait=True, cancel_futures=False)
    results = [future.result() for future in futures]

    return results


def map_shape(shape, previous_shape_names: list = None):
    try:
        if previous_shape_names is None:
            previous_shape_names = []

        previous_shape_names.append(shape.name)

        if shape.type_name == 'structure':
            return {
                member_name: map_shape(member_shape, previous_shape_names)
                for member_name, member_shape
                in shape.members.items()
            }

        elif shape.type_name == 'list':
            return [
                map_shape(shape.member, previous_shape_names)
            ]

        elif shape.type_name == 'map':
            return {
                shape.key.type_name: map_shape(shape.value, previous_shape_names)
            }

        else:
            if hasattr(shape, 'enum'):
                if len(shape.enum) > 0:
                    return f'enum({"|".join(shape.enum)})'

                else:
                    result = shape.type_name

                    del shape
                    previous_shape_names.clear()

                    return result

            else:
                result = shape.type_name

                del shape
                previous_shape_names.clear()

                return result

    except Exception as ex:
        print(f'could not map shape {shape.name} in chain ({".".join(previous_shape_names)}): {ex}')
        return None


def map_aws_service(service: str):
    print(service)

    operations = []

    client = session.client(service)
    service_model = client.meta.service_model

    for operation_name in service_model.operation_names:
        operation_model = service_model.operation_model(operation_name)
        input_shape = operation_model.input_shape
        output_shape = operation_model.output_shape
        try:
            result = {
                'input': map_shape(input_shape),
                'output': map_shape(output_shape)
            }

            operations.append(operation_name)

        except Exception as ex:
            print(f'could not map {service}.{operation_name}: {ex}')

        else:
            print(f'mapped {service}.{operation_name}')

            with open(f'./cache/{service}.{operation_name}.json', 'w') as stream:
                from json import dump
                dump(result, stream, indent=4, default=str)

    return {
        service: operations
    }


if __name__ == '__main__':
    session = boto3.Session(region_name='us-east-1')

    from pprint import pprint
    pprint(len(map_aws_services()))
