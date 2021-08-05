import os
import re
import sys
from codecs import open

from setuptools import find_packages, setup

# 'setup.py publish' shortcut.
if sys.argv[-1] == 'publish':
    os.system('python3 setup.py sdist bdist_wheel')
    os.system('twine upload dist/*')
    sys.exit()


def get_readme():
    readme = ''
    with open('README.md', 'r', 'utf-8') as f:
        readme = f.read()
    return readme


def get_info(info_name):
    init_py = open(os.path.join('django_restql', '__init__.py')).read()
    return re.search("%s = ['\"]([^'\"]+)['\"]" % info_name, init_py).group(1)


url = get_info('__url__')
version = get_info('__version__')
license_ = get_info('__license__')
description = get_info('__description__')
author = get_info('__author__')
author_email = get_info('__author_email__')
readme = get_readme()

setup(
    name='django-restql',
    version=version,
    description=description,
    long_description=readme,
    long_description_content_type='text/markdown',
    url=url,
    author=author,
    author_email=author_email,
    license=license_,
    packages=find_packages(exclude=('tests', 'test')),
    package_data={'': ['LICENSE']},
    install_requires=[
        'pypeg2>=2.15.2',
        'django>=1.11',
        'djangorestframework>=3.5'
    ],
    python_requires='>=3.5',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: MIT License',
        'Framework :: Django',
        'Framework :: Django :: 1.11',
        'Framework :: Django :: 2.0',
        'Framework :: Django :: 2.1',
        'Framework :: Django :: 2.2',
        'Framework :: Django :: 3.0',
        'Framework :: Django :: 3.1',
        'Framework :: Django :: 3.2',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: 3.8',
        'Programming Language :: Python :: 3.9',
    ],
    test_suite='runtests',
)
