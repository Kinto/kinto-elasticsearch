#!/usr/bin/env python
# -*- coding: utf-8 -*-
from setuptools import setup


with open('README.rst') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.rst') as history_file:
    history = history_file.read()

REQUIREMENTS = [
    'elasticsearch',
    'kinto>=6.0.0'
]

TEST_REQUIREMENTS = [
    'mock',
    'unittest2',
    'webtest',
]

ENTRY_POINTS = {
    'console_scripts': [
        'kinto-elasticsearch-reindex = kinto_elasticsearch.command_reindex:main'
    ],
}

setup(
    name='kinto-elasticsearch',
    version='0.3.1',
    description="Index and search records using ElasticSearch.",
    long_description=readme + '\n\n' + history,
    author='Mozilla Services',
    author_email='services-dev@mozilla.com',
    url='https://github.com/kinto/kinto-elasticsearch',
    packages=[
        'kinto_elasticsearch',
    ],
    package_dir={'kinto_elasticsearch': 'kinto_elasticsearch'},
    include_package_data=True,
    install_requires=REQUIREMENTS,
    license="Apache License (2.0)",
    zip_safe=False,
    keywords='kinto elasticsearch index',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],
    test_suite='tests',
    tests_require=TEST_REQUIREMENTS,
    entry_points=ENTRY_POINTS
)
