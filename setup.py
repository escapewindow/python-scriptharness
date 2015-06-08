#!/usr/bin/env python
"""setup.py for scriptharness
"""
from __future__ import print_function, division, absolute_import, \
                       unicode_literals
import json
import os
from setuptools import setup, find_packages
import subprocess
import sys


# Version
PATH = os.path.join(os.path.dirname(__file__), "version.json")
if not os.path.exists(PATH):
    subprocess.check_call(
        [sys.executable, os.path.join(os.path.dirname(__file__),
                                      "scriptharness", "version.py")]
    )
with open(PATH) as filehandle:
    VERSION = json.load(filehandle)['version_string']
if sys.version_info < (2, 7) or (sys.version_info[0] == 3 and
                                 sys.version_info[1] < 3):
    print('ERROR: scriptharness requires Python 2.7 or 3.3+! Exiting...')
    sys.exit(1)


def get_dependencies():
    """Dependency list
    """
    dependencies = ['requests', 'six', 'psutil']
    if os.name == 'nt':
        dependencies.append('win_unicode_console')


def read(fname):
    """http://pythonhosted.org/an_example_pypi_project/setuptools.html"""
    return open(os.path.join(os.path.dirname(__file__), fname)).read()


setup(
    name='scriptharness',
    version=VERSION,
    description='A generic logging, configuration, and workflow framework for scripts.',
    long_description=read('README'),
    author='Aki Sasaki',
    author_email='aki@escapewindow.com',
    url='https://github.com/scriptharness/scriptharness',
    license='MPL2',
    packages=find_packages(exclude=['ez_setup', 'examples', 'tests']),
    include_package_data=True,
    zip_safe=False,
    install_requires=get_dependencies(),
    entry_points="""
# -*- Entry points: -*-
""",
    platforms=["Posix", "MacOS X", "Windows"],
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "Natural Language :: English",
        "Operating System :: MacOS :: MacOS X",
        "Operating System :: Microsoft :: Windows",
        "Operating System :: POSIX",
        "Operating System :: POSIX :: BSD",
        "Operating System :: POSIX :: Linux",
        "Topic :: Software Development",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: Implementation :: PyPy",
    ],
)
