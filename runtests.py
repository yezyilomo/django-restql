#!/usr/bin/env python
import os
import sys
import subprocess

from django.core.management import execute_from_command_line


FLAKE8_ARGS = ['django_restql', 'tests', 'setup.py', 'runtests.py']
WARNING_COLOR = '\033[93m'
END_COLOR = '\033[0m'


def flake8_main(args):
    print('Running flake8 code linting')
    ret = subprocess.call(['flake8'] + args)
    msg = (
        WARNING_COLOR + 'flake8 failed\n' + END_COLOR
        if ret else 'flake8 passed\n'
    )
    print(msg)
    return ret


def runtests():
    ret = flake8_main(FLAKE8_ARGS)
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tests.settings')
    argv = sys.argv[:1] + ['test'] + sys.argv[1:]
    execute_from_command_line(argv)
    sys.exit(ret)  # Fail build if code linting fails


if __name__ == '__main__':
    runtests()
