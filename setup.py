from setuptools import setup, find_packages

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

config = dict(name='CloudHarvestPluginAws',
              version='0.1.0',
              description='This is the AWS Plugin for CloudHarvest.',
              author='Cloud Harvest, Fiona June Leathers',
              url='https://github.com/Cloud-Harvest/CloudHarvestPluginAws',
              packages=find_packages(include=['CloudHarvestPluginAws']),
              install_requires=requirements,
              classifiers=[
                  'Programming Language :: Python :: 3.12',
              ],
              entry_points={
                  'console_scripts': [
                      'cloudharvestpluginaws=install_saml2aws:main',
                  ],
              })


def main():
    setup(**config)


if __name__ == '__main__':
    main()
