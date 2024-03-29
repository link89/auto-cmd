#!/usr/bin/env python

import sys

from setuptools import find_packages, setup

description = 'Cross-platform CLI tools and HTTP RPC server for desktop automation.'

install_requirements = [
    'fire',
    'fastapi',
    'pynput',
    'uvicorn',
    'pytesseract',
    'Pillow',
    'pyvirtualcam',
    'numpy',
    'mss',
    'pandas',
    'scikit-learn',
    'scipy',
    'psutil',
    'guibot',
    'autopy',
]

if sys.platform == 'darwin':
    install_requirements.extend([
        "pyobjc-framework-Quartz==7.3",
        "pyobjc-core==7.3",
        "pyobjc-framework-ApplicationServices==7.3",
        "pyobjc-framework-Cocoa==7.3",
        "pyobjc-framework-CoreText==7.3",
        "pyobjc-framework-Quartz==7.3",
        'atomac @ https://github.com/pyatom/pyatom/archive/master.zip',
    ])

if sys.platform.startswith('win'):
    install_requirements.extend([
        "pywinauto",
    ])

setup(
    name='auto-cmd',
    author='link89',
    author_email='xuweihong.cn@gmail.com',
    version='0.0.8',
    packages=find_packages(),
    description=description,
    long_description=description,
    install_requires=install_requirements,
    entry_points={
        'console_scripts': [
            'auto-cmd=auto_cmd.cli:main',
            'auto-cmd-http=auto_cmd.http_server:main',
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