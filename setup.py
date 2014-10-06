# -*- coding: utf-8 -*-
#
# This file is part of Lumberjack.
# Copyright (C) 2014 CERN.
#
# Lumberjack is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the
# License, or (at your option) any later version.
#
# Lumberjack is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Lumberjack; if not, write to the Free Software Foundation, Inc.,
# 59 Temple Place, Suite 330, Boston, MA 02111-1307, USA.

from setuptools import setup
import os
import re

# Get the version string.  Cannot be done with import!
with open(os.path.join('lumberjack', 'version.py'), 'rt') as f:
    version = re.search(
        '__version__\s*=\s*"(?P<version>.*)"\n',
        f.read()
    ).group('version')

setup(
    name='Lumberjack',
    version=version,
    url='http://github.com/jmacmahon/lumberjack',
    license='GPL',
    author='Joe MacMahon',
    author_email='joe.macmahon@cern.ch',
    description='Lumberjack is a library which provides an interface between '
        'the Python logging framework and Elasticsearch.',
    long_description=open('README.rst').read(),
    packages=['lumberjack'],
    zip_safe=False,
    include_package_data=True,
    platforms='any',
    install_requires=[
        'elasticsearch',
    ],
    classifiers=[
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License (GPL)',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Development Status :: 3 - Alpha',
    ],
    test_suite='nose.collector',
    tests_require=['nose', 'coverage'],
)
