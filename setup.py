#!/usr/bin/env python
from setuptools import setup, find_packages
from setuptools.command.install import install as _install
import os
import stat

EXECUTABLE_FILES=('dvcs/mercurial/mergetool.py', 'dvcs/mercurial/difftool.py')

class install(_install):
    def run(self):
        _install.run(self)
        for filename in open(self.record,'r'):
            for ef in EXECUTABLE_FILES:
                if filename.strip().endswith(ef):
                    os.chmod(filename.strip(), stat.S_IRWXU|stat.S_IRWXG|stat.S_IROTH) #executable by owner, group, readable by others

            

    
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
    version = '1.0.1',
    description = """Set of DVCS wrappers (currently only hg)""",
    author = 'starenka, vlinhart',
    url = "https://github.com/outcomm/dvcswrapper",
    packages = find_packages(),
    download_url = "https://github.com/outcomm/dvcswrapper",
    classifiers = CLASSIFIERS,
    keywords = KEYWORDS,
    zip_safe = False,
    include_package_data = True,
    install_requires = ['fabric<1.4.0', 'mercurial>=2.1.1', 'python-dateutil==1.5'], #dateutil > 1.5 for py3k
    cmdclass={'install': install},
)

