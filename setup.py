#
# Copyright 2017 University of Southern California
# Distributed under the Apache License, Version 2.0. See LICENSE for more info.
#

""" Installation script for the deriva package.
"""

from setuptools import setup, find_packages
import re
import io

__version__ = re.search(
    r'__version__\s*=\s*[\'"]([^\'"]*)[\'"]',
    io.open('deriva/workbench/__init__.py', encoding='utf_8_sig').read()
    ).group(1)


def get_readme_contents():
    with io.open('README.md') as readme_file:
        return readme_file.read()


url = "https://github.com/informatics-isi-edu"
author = 'USC Information Sciences Institute, Informatics Systems Research Division'
author_email = 'isrd-support@isi.edu'


setup(
    name='deriva-workbench',
    description='Schema Workbench for the DERIVA platform.',
    long_description='For further information, visit the project [homepage](%s).' % url,
    long_description_content_type='text/markdown',
    url=url,
    author=author,
    author_email=author_email,
    maintainer=author,
    maintainer_email=author_email,
    version=__version__,
    packages=find_packages(exclude=["tests"]),
    package_data={'deriva.workbench': ['icons/*']},
    entry_points={
        'console_scripts': [
            'deriva-workbench = deriva.workbench.__main__:main',
        ]
    },
    install_requires=[
        'deriva>=1.5.0',
        'deriva-qt>=1.5.0'
    ],
    extras_require={
        'PyQt5': ["PyQt5==5.11.3"],
        'PyQtWebEngine': ["PyQtWebEngine>=5.15.4"],
        'PyQt5-stubs': ["PyQt5-stubs<5.12"],
        'PyQtWebEngine-stubs': ["PyQt5-stubs>=5.15"]
    },
    license='GNU GPL 3.0',
    classifiers=[
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Operating System :: POSIX',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: Microsoft :: Windows',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.7'
    ]
)
