# django-restql

[![Latest Version](https://img.shields.io/pypi/v/django-restql.svg)](https://pypi.org/project/django-restql/)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-restql.svg)](https://pypi.org/project/django-restql/)
[![License](https://img.shields.io/pypi/l/django-restql.svg)](https://pypi.org/project/django-restql/)

**django-restql** is a python library which allows django-rest-framework to dynamically select only a subset of fields per DRF resource(Support both flat and nested resources)

## Installing
For python3
```python
pip3 install dictfier
```

For python2
```python
pip install dictfier
```

## Getting Started
Using **django-restql** is very simple, you just have to use the DynamicFieldsMixin when defining a serializer.
```python
from rest_framework import serializers
from django.contrib.auth.models import User
from django_restql.mixins import DynamicFieldsMixin

class UserSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'groups')
```

A regular request returns all fields:

```GET /users```

``` json
    [
      {
        "id": 1,
        "username": "yezyilomo",
        "email": "yezileliilomo@hotmail.com",
        "groups": [1,2]
      },
      ...
    ]
```

A request with the `query` parameter on the other hand returns only a subset of
the fields:

```GET /users/?query=["id", "username"]```

```json
    [
      {
        "id": 1,
        "username": "yezyilomo"
      },
      ...
    ]
```

With **django-restql** you can access nested fields of any level. E.g

```GET /users/?query=["id", "username" {"date_joined": ["year"]}]```

```json
    [
      {
        "id": 1,
        "username": "yezyilomo",
        "date_joined": {
            "year": 2018
        }
      },
      ...
    ]
```

**django-restql** got your back on iterable nested fields too. E.g

```GET /users/?query=["id", "username" {"groups": [[ "id", "name" ]]}]```

```json
    [
      {
        "id": 1,
        "username": "yezyilomo",
        "groups": [
            {
                "id": 2,
                "name": "Auth_User"
            }
        ]
      },
      ...
    ]
```

**Warnings** 
If the request context does not have access to the request, a warning is emitted:

```UserWarning: Context does not have access to request.```

First, make sure that you are passing the request to the serializer context

## Credits
This implementation is based on [dictfier](https://github.com/yezyilomo/dictfier) library and the idea behind GraphQL. 

My intention was to extend the capability of [drf-dynamic-fields](https://github.com/dbrgn/drf-dynamic-fields) library to support more functionalities like allowing to query nested fields both flat and iterable.