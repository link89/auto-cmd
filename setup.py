#!/usr/bin/env python

import ast
import re
import subprocess
import sys

from setuptools import find_packages, setup


description = 'Cross-platform CLI tools and HTTP RPC server for desktop automation.'

install_requirements = [
    'fire',
    'falcon',
    'pyparsing',
    'pynput',
]

if sys.platform == 'darwin':
    install_requirements.extend([
        'atomac @ https://github.com/pyatom/pyatom/archive/master.zip',
    ])

setup(
    name='auto-cmd',
    author='link89',
    author_email='xuweihong.cn@gmail.com',
    version='0.0.1',
    url='http://mycli.net',
    packages=find_packages(),
    description=description,
    long_description=description,
    install_requires=install_requirements,
    entry_points={
        'console_scripts': [
            'auto_cmd=auto_cmd.main:cli',
        ],
    },
    python_requires=">=3.6",
    classifiers=[
        'Intended Audience :: Developers',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
    ],
)
