from typing import List
from logging import getLogger

logger = getLogger('harvest')


def write_credentials(results: List[dict], output_path):
    """
    Writes the AWS credentials to a specified output path.

    This method takes a list of dictionaries containing AWS credentials and writes them to a file specified by the output_path attribute. Each dictionary in the list represents a set of credentials for a specific AWS profile.
    """

    from configparser import ConfigParser

    # Create a new ConfigParser object
    config = ConfigParser()

    # Iterate over the login results
    for result in results:
        # Get the profile name from the result
        profile = result['Profile']

        # Add a new section to the ConfigParser for this profile
        # and set the AWS credentials in this section
        config[profile] = {
            'aws_access_key_id': result['AccessKeyId'],
            'aws_secret_access_key': result['SecretAccess'],
            'aws_session_token': result['SessionToken'],
            'expiration': result['Expiration'],
        }

    # Open the output file in write mode
    with open(output_path, 'w') as configfile:
        # Write the configuration to the file
        config.write(configfile)

    # Log the number of credentials written to the file
    logger.debug(f'Wrote {len(results)} credentials to {output_path}')