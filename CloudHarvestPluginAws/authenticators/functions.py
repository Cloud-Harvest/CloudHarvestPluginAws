from logging import getLogger
from typing import List

logger = getLogger('harvest')





def aws_role_arn_from_profile(profile: str) -> str:
    """
    Get the AWS role ARN from the profile_name.

    Args:
        profile (str): The AWS profile_name profile_name.
    """

    from boto3 import Session

    session = Session(profile_name=profile)

    client = session.client('sts')
    response = client.get_caller_identity()

    return response['Arn']





def get_role_duration(requesting_profile: str, target_role_arn: str) -> int:
    """
    Get the role duration.

    Args:
        requesting_profile (dict): The requesting role.
        target_role_arn (str): The target role ARN.

    Example:
        >>> get_role_duration(requesting_profile='harvest-role',
        >>>                   target_role_arn='arn:aws:iam::123456789012:role/harvest-role')
    """

    from tasks import AwsTask
    request = AwsTask(profile=requesting_profile,
                      region=None,
                      service='iam',
                      command='get_role',
                      arguments={
                          'RoleName': target_role_arn.split('/')[-1]
                      },
                      result_key='Role')

    response = request.run().data.get('MaxSessionDuration')

    return response
