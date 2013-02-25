# -*- coding: utf-8 -*-
import os
from setuptools import setup, find_packages

def read(fname):
    try:
        return open(os.path.join(os.path.dirname(__file__), fname)).read()
    except:
        return ''

setup(
    name='python-resources',
    version='0.2',
    py_modules=['resources'],
    author='Roman Imankulov',
    author_email='roman.imankulov@gmail.com',
    license='BSD',
    url='https://github.com/doist/resources',
    description=' A fixture lifecycle management library for your tests',
    long_description = read('README.rst'),
    # see here for complete list of classifiers
    # http://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=(
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: BSD License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.6',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3.3',
        'Topic :: Software Development :: Testing',
    ),
)
