"""
This test suite requires a valid AWS account and role to run as well as the following environment variables:
- AWS_ACCOUNT
- AWS_REGION (default: us-east-1)
- AWS_ROLE (default: harvest)
"""


import unittest


class TestProfiles(unittest.TestCase):
    def test_get_profile(self):
        from os import environ
        from CloudHarvestPluginAws.credentials import get_profile

        # Get the profile
        profile = get_profile(
            account_number=environ.get('AWS_ACCOUNT'),
            role_name=environ.get('AWS_ROLE') or 'harvest'
        )

        # Check the profile is not None
        self.assertIsNotNone(profile)

        # Check the profile has the expected attributes
        self.assertIsNotNone(profile.aws_access_key_id)
        self.assertIsNotNone(profile.aws_secret_access_key)
        self.assertIsNotNone(profile.aws_session_token)
        self.assertIsNotNone(profile.account_alias)
        self.assertIsNotNone(profile.account_number)
        self.assertIsNotNone(profile.expiration)
        self.assertIsNotNone(profile.role_name)
        self.assertIsNotNone(profile.role_arn)
