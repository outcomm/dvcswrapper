#!/usr/bin/env python
from setuptools import setup, find_packages

CLASSIFIERS = [
    'Development Status :: 5 - Production/Stable',
    'Intended Audience :: Developers',
    'License :: OSI Approved :: MIT License',
    'Natural Language :: English',
    'Operating System :: OS Independent',
    'Programming Language :: Python',
    'Topic :: Software Development :: Libraries :: Python Modules'
]

KEYWORDS = 'Set of DVCS wrappers (currently only hg)'


setup(name = 'dvcs',
    version = '1.0.0',
    description = """Set of DVCS wrappers (currently only hg)""",
    author = 'starenka, vlinhart',
    url = "https://github.com/outcomm/dvcswrapper",
    packages = find_packages(),
    download_url = "https://github.com/outcomm/dvcswrapper",
    classifiers = CLASSIFIERS,
    keywords = KEYWORDS,
    zip_safe = True,
    install_requires = ['fabric<1.4.0','mercurial>=2.1.1',]
)