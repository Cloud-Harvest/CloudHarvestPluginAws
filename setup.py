from setuptools import setup, find_packages
from CloudHarvestPluginAws.meta import meta

with open('requirements.txt') as f:
    requirements = f.read().splitlines()

config = dict(packages=find_packages(include=['CloudHarvestPluginAws', 'CloudHarvestPluginAws.*']),
              install_requires=requirements,
              include_package_data=True)

config = config | meta


def main():
    setup(**config)


if __name__ == '__main__':
    main()
