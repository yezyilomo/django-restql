from codecs import open
from setuptools import setup, find_packages

DESCRIPTION = """
    Dynamically select only a subset of fields per DRF resource(Support both flat and nested resources)
    """
with open('README.md', 'r', 'utf-8') as f:
    readme = f.read()

REQUIRES_PYTHON = '>=2.7'

setup(
    name = 'django-restql',
    version = '0.2.0',
    description = DESCRIPTION,
    long_description = readme,
    long_description_content_type = 'text/markdown',
    url = "https://github.com/yezyilomo/django-restql",
    author = 'Yezy Ilomo',
    author_email = 'yezileliilomo@hotmail.com',
    license = 'MIT',
    packages = find_packages(exclude=('tests','test')),
    package_data={'': ['LICENSE']},
    install_requires = ['dictfier', 'djangorestframework'],
    python_requires = REQUIRES_PYTHON,
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'Natural Language :: English',
        'License :: OSI Approved :: Apache Software License',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
        'Programming Language :: Python :: Implementation :: CPython',
        'Programming Language :: Python :: Implementation :: PyPy'
    ],
    test_suite = "tests",
)
