from setuptools import setup, find_packages

with open('requirements.txt', 'r') as f:
    requirements = f.read().splitlines()

setup(
    name='CloudHarvestApi',
    version='0.1.0',
    description='This is the AWS plugin for CloudHarvest, useful for both clients and the API.',
    author='Cloud Harvest',
    url='https://github.com/Cloud-Harvest/CloudHarvestPluginAws',
    packages=find_packages(exclude=['tests', 'tests.*']),
    install_requires=requirements,
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.12',
    ],
)
