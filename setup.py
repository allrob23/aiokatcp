#!/usr/bin/env python3

# Copyright 2017 National Research Foundation (Square Kilometre Array)
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# 1. Redistributions of source code must retain the above copyright notice, this
# list of conditions and the following disclaimer.
#
# 2. Redistributions in binary form must reproduce the above copyright notice,
# this list of conditions and the following disclaimer in the documentation
# and/or other materials provided with the distribution.
#
# 3. Neither the name of the copyright holder nor the names of its contributors
# may be used to endorse or promote products derived from this software without
# specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

from setuptools import find_packages, setup

tests_require = ['async-solipsism', 'pytest', 'pytest-asyncio', 'pytest-mock']
docs_require = ['sphinx', 'sphinx-autodoc-typehints', 'sphinxcontrib-asyncio', 'sphinx-rtd-theme']

setup(
    name='aiokatcp',
    use_katversion=True,
    packages=find_packages('src'),
    package_dir={'': 'src'},
    package_data={'aiokatcp': ['py.typed']},
    author='Bruce Merry',
    author_email='bmerry@ska.ac.za',
    description='Asynchronous I/O implementation of the katcp protocol',
    url='https://github.com/ska-sa/aiokatcp',
    license='BSD',
    platforms=['OS Independent'],
    keywords='asyncio katcp',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Framework :: AsyncIO',
        'License :: OSI Approved :: BSD License',
        'Operating System :: OS Independent',
        'Programming Language :: Python :: 3',
        'Topic :: Software Development :: Libraries :: Python Modules',
        'Topic :: Scientific/Engineering :: Astronomy'
    ],
    tests_require=tests_require,
    install_requires=['decorator>=4.1', 'async-timeout'],
    setup_requires=['katversion'],
    extras_require={
        'test': tests_require,
        'doc': docs_require
    },
    entry_points={
        'console_scripts': [
            'katcpcmd = aiokatcp.tools.katcpcmd:main'
        ]
    },
    python_requires='>=3.7',
    zip_safe=False   # For py.typed
)
