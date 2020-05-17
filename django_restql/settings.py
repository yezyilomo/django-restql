"""
Settings for Django RESTQL are all namespaced in the RESTQL setting.
For example your project's `settings.py` file might look like this:
RESTQL = {
    'QUERY_PARAM_NAME': 'query'
}
This module provides the `restql_settings` object, that is used to access
Django RESTQL settings, checking for user settings first, then falling
back to the defaults.
"""
from django.conf import settings
from django.test.signals import setting_changed
from django.utils.module_loading import import_string

DEFAULTS = {
    'QUERY_PARAM_NAME': 'query',
    'AUTO_APPLY_EAGER_LOADING': True,
}


# List of settings that may be in string import notation.
IMPORT_STRINGS = [

]


def perform_import(val, setting_name):
    """
    If the given setting is a string import notation,
    then perform the necessary import or imports.
    """
    if val is None:
        return None
    elif isinstance(val, str):
        return import_from_string(val, setting_name)
    elif isinstance(val, (list, tuple)):
        return [import_from_string(item, setting_name) for item in val]
    return val


def import_from_string(val, setting_name):
    """
    Attempt to import a class from a string representation.
    """
    try:
        return import_string(val)
    except ImportError as e:
        msg = (
            "Could not import '%s' for RESTQL setting '%s'. %s: %s."
        ) % (val, setting_name, e.__class__.__name__, e)
        raise ImportError(msg)


class RESTQLSettings:
    """
    A settings object, that allows RESTQL settings to be accessed as properties.
    For example:
        from django_restql.settings import restql_settings
        print(restql_settings.QUERY_PARAM_NAME)
    Any setting with string import paths will be automatically resolved
    and return the class, rather than the string literal.
    """

    def __init__(self, user_settings=None, defaults=None, import_strings=None):
        self.defaults = defaults or DEFAULTS
        self.import_strings = import_strings or IMPORT_STRINGS
        self._cached_attrs = set()

    @property
    def user_settings(self):
        if not hasattr(self, '_user_settings'):
            self._user_settings = getattr(settings, 'RESTQL', {})
        return self._user_settings

    def __getattr__(self, attr):
        if attr not in self.defaults:
            raise AttributeError("Invalid RESTQL setting: '%s'" % attr)

        try:
            # Check if present in user settings
            val = self.user_settings[attr]
        except KeyError:
            # Fall back to defaults
            val = self.defaults[attr]

        # Coerce import strings into classes
        if attr in self.import_strings:
            val = perform_import(val, attr)

        # Cache the result
        self._cached_attrs.add(attr)
        setattr(self, attr, val)
        return val

    def reload(self):
        for attr in self._cached_attrs:
            delattr(self, attr)
        self._cached_attrs.clear()
        if hasattr(self, '_user_settings'):
            delattr(self, '_user_settings')


restql_settings = RESTQLSettings(None, DEFAULTS, IMPORT_STRINGS)


def reload_restql_settings(*args, **kwargs):
    setting = kwargs['setting']
    if setting == 'RESTQL':
        restql_settings.reload()


setting_changed.connect(reload_restql_settings)
