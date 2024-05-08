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
                  'Development Status :: 3 - Alpha',
                  'Intended Audience :: Developers',
                  'License :: OSI Approved :: MIT License',
                  'Programming Language :: Python :: 3.12',
              ],
              entry_points={
                  'console_scripts': [
                      'cloudharvestpluginaws=install_saml2aws:main',
                  ],
              })

setup(**config)
