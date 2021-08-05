import tests
from django.apps import AppConfig


class TestappConfig(AppConfig):
    name = 'tests.testapp'
    default_auto_field = 'django.db.models.BigAutoField'
