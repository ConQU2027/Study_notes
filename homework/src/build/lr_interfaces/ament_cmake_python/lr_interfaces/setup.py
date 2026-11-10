from setuptools import find_packages
from setuptools import setup

setup(
    name='lr_interfaces',
    version='0.0.0',
    packages=find_packages(
        include=('lr_interfaces', 'lr_interfaces.*')),
)
