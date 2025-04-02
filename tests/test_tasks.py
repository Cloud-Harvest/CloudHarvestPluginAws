from CloudHarvestPluginAws.tasks import AwsTask

import unittest

"""
Testing with this file requires environment variables to be set.

HARVEST_TEST_AWS_ACCOUNT_NUMBER
HARVEST_TEST_AWS_ACCOUNT_ROLE       (optional, default 'harvest')
HARVEST_TEST_AWS_ACCOUNT_REGION     (optional, default 'us-east-1')
"""


class TestAwsTask(unittest.TestCase):
    def setUp(self):
        from os import environ

        self.account_number = environ.get('HARVEST_TEST_AWS_ACCOUNT_NUMBER')
        self.account_role = environ.get('HARVEST_TEST_AWS_ACCOUNT_ROLE') or 'harvest'
        self.account_region = environ.get('HARVEST_TEST_AWS_ACCOUNT_REGION') or 'us-east-1'

    def test_aws_task(self):
        task = AwsTask(
            name='Test AwsTask',
            description='Test AwsTask',
            service='iam',
            type='role',
            account=self.account_number,
            region=self.account_region,
            command='list_roles',
            arguments={},
            role=self.account_role
    )

        task.run()

        result = task.data

        # Check there are no errors
        self.assertFalse(task.errors)

        # Check the result is not None
        self.assertIsNotNone(result)

        # Check that the account alias was populated
        self.assertNotEqual(task.account_alias, task.account)
