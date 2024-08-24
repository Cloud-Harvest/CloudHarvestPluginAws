import unittest
import tempfile
import os
from configparser import ConfigParser
from ..CloudHarvestPluginAws.authenticators.functions import read_aws_configuration_file, write_aws_configuration_file

class TestAWSConfigurationFunctions(unittest.TestCase):

    def setUp(self):
        # Create a temporary file
        self.temp_file = tempfile.NamedTemporaryFile(delete=False)
        self.temp_file.close()

        # In-code test data with simulated data
        self.test_data = {
            'default': {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY'
            },
            'profile1': {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE1',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY1',
                'aws_session_token': 'AQoDYXdzEJr...<remainder of security token>'
            },
            'profile2': {
                'aws_access_key_id': 'AKIAIOSFODNN7EXAMPLE2',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY2',
                'aws_session_token': 'AQoDYXdzEJr...<remainder of security token>'
            }
        }

        # Write test data to the temporary file
        config = ConfigParser()
        config.read_dict(self.test_data)
        with open(self.temp_file.name, 'w') as file:
            config.write(file)

    def tearDown(self):
        # Remove the temporary file
        os.remove(self.temp_file.name)

    def test_read_aws_configuration_file(self):
        # Read the configuration from the temporary file
        config = read_aws_configuration_file(self.temp_file.name)

        # Validate the read configuration
        for section in self.test_data:
            self.assertIn(section, config)
            for key, value in self.test_data[section].items():
                self.assertEqual(config[section][key], value)

    def test_read_aws_configuration_file_regex(self):
        # Read the configuration from the temporary file
        config = read_aws_configuration_file(self.temp_file.name, profile_regex='profile1')

        # Validate the read configuration
        for key, value in self.test_data['profile1'].items():
            self.assertEqual(config['profile1'][key], value)

    def test_write_aws_configuration_file(self):
        # Modify the test data with simulated data
        modified_data = {
            'default': {
                'aws_access_key_id': 'AKIAIOSFODNN7MODIFIED',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYMODIFIEDKEY'
            },
            'profile1': {
                'aws_access_key_id': 'AKIAIOSFODNN7MODIFIED1',
                'aws_secret_access_key': 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYMODIFIEDKEY1',
                'aws_session_token': 'AQoDYXdzEJr...<remainder of modified security token>'
            }
        }

        # Write the modified data to the temporary file
        write_aws_configuration_file(self.temp_file.name, modified_data)

        # Read the configuration from the temporary file
        config = read_aws_configuration_file(self.temp_file.name)

        # Validate the written configuration
        for section in modified_data:
            self.assertIn(section, config)
            for key, value in modified_data[section].items():
                self.assertEqual(config[section][key], value)

if __name__ == '__main__':
    unittest.main()