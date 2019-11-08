from codecs import open
from setuptools import setup, find_packages

DESCRIPTION = "Turn your API made with Django REST Framework(DRF) into a GraphQL like API."
with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

REQUIRES_PYTHON = '>=3.5'

setup(
    name = 'django-restql',
    version = '0.5.3',
    description = DESCRIPTION,
    long_description = readme,
    long_description_content_type = 'text/markdown',
    url = "https://github.com/yezyilomo/django-restql",
    author = 'Yezy Ilomo',
    author_email = 'yezileliilomo@hotmail.com',
    license = 'MIT',
    packages = find_packages(exclude=('tests','test')),
    package_data = {'': ['LICENSE']},
    install_requires = ['pypeg2', 'djangorestframework'],
    python_requires = REQUIRES_PYTHON,
    classifiers = [
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    test_suite = "tests.runtests.runtests",
)
