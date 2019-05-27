import os
import sys

import django
from django.conf import settings
from django.test.utils import get_runner


def runtests(*test_args):
    if not test_args:
        test_args = ['tests']

    os.environ['DJANGO_SETTINGS_MODULE'] = 'tests.settings'
    django.setup()
    test_runner = get_runner(settings)()
    failures = test_runner.run_tests(test_args)
    sys.exit(bool(failures))


if __name__ == '__main__':
    runtests(*sys.argv[1:])
