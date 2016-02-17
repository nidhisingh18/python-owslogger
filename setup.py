from setuptools import find_packages
from setuptools import setup


setup(
    name='owslogger',
    version='0.3.0',
    url='https://github.com/theorchard/python-owslogger/',
    author='The Orchard',
    description=(
        'Logging library.'),
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'requests-futures'],
    zip_safe=False,
    classifiers=[
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
    ],)
