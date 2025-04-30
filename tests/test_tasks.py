"""
This test suite requires a valid AWS account and role to run as well as the following environment variables:
- AWS_ACCOUNT
- AWS_REGION (default: us-east-1)
- AWS_ROLE (default: harvest)
"""

from CloudHarvestPluginAws.tasks import AwsTask

import unittest


class TestAwsTask(unittest.TestCase):
    def test_aws_task(self):
        from os import environ

        task = AwsTask(
            name='Test AwsTask',
            description='Test AwsTask',
            service='account',
            type='region',
            account=environ.get('AWS_ACCOUNT'),
            region=environ.get('AWS_REGION') or 'us-east-1',
            command='list_regions',
            arguments={},
            role=environ.get('AWS_ROLE') or 'harvest',
    )

        task.run()

        # Check there are no errors
        self.assertFalse(task.errors)

        # Check the result is not None
        self.assertIsNotNone(task.result)

        # Check that the account alias was populated
        self.assertNotEqual(task.account_alias, task.account)
