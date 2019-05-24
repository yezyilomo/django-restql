# django-restql

[![Latest Version](https://img.shields.io/pypi/v/django-restql.svg)](https://pypi.org/project/django-restql/)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-restql.svg)](https://pypi.org/project/django-restql/)
[![License](https://img.shields.io/pypi/l/django-restql.svg)](https://pypi.org/project/django-restql/)

**django-restql** is a python library which allows you to turn your API made with **Django REST Framework(DRF)** into a GraphQL like API. With this you will be able to
* Send a query to your API and get exactly what you need, nothing more and nothing less.

* Control the data you get, not the server.

* Get predictable results, since you control what you get from the server.

* Save the load of fetching unused data from the server.

Isn't it cool?.

**django-restql** works by selecting dynamically a subset of fields per DRF resource as specified by the request's `query` parameter.

## Installing

```python
pip install django-restql
```

## Getting Started
Using **django-restql** is very simple, you just have to use the DynamicFieldsMixin when defining a View.
```python
from rest_framework import viewsets
from django.contrib.auth.models import User
from .serializers import UserSerializer
from django_restql import DynamicFieldsMixin

class UserViewSet(DynamicFieldsMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
```

A regular request returns all fields specified on DRF serializer, in fact **django-restql** doesn't handle this request at all:

`GET /users`

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

**django-restql** handle all GET requests with `query` parameter, this parameter is the one used to pass all fields to be included on a response. For example to select `id` and `username` fields from `user` model, send a request with a ` query` parameter as shown below.

`GET /users/?query={id, username}`

```json
    [
      {
        "id": 1,
        "username": "yezyilomo"
      },
      ...
    ]
```

If a query contains nested field, **django-restql** will return its id or array of ids for the case of nested iterable field(one2many or many2many). For example on a request below `location` is a flat nested field(many2one) and `groups` is an iterable nested field(one2many or many2many).

`GET /users/?query={id, username, location, group}`

```json
    [
      {
        "id": 1,
        "username": "yezyilomo",
        "location": 6,
        "groups": [1,2]
      },
      ...
    ]
```

**django-restql** support querying both flat and nested resources, so you can expand or query nested fields at any level as long as your field is defined as nested field on a serializer. For example you can query a country and region field from location.

`GET /users/?query={id, username, location{country, region}}`

```json
    [
      {
        "id": 1,
        "username": "yezyilomo",
        "location": {
            "contry": "Tanzania",
            "region": "Dar es salaam"
        }
      },
      ...
    ]
```

**django-restql** got your back on expanding or querying iterable nested fields too. For example if you want to expand `groups` field into `id` and `name`, here is how you would do it.

`GET /users/?query={id, username, groups{id, name}}`

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
            {
                "id": 3,
                "name": "Admin_User"
            }
        ]
      },
      ...
    ]
```

## Customizing django-restql
**django-restql**  is very configurable, here is what you can customize
* Change the name of ```query``` parameter.

    If you don't want to use the name ```query``` as your parameter, you can inherit `DynamicFieldsMixin` and change it as shown below
    ```python
    from django_restql.mixins import DynamicFieldsMixin

    class MyDynamicFieldMixin(DynamicFieldsMixin):
        query_param_name = "your_favourite_name"
     ```
     Now you can use this Mixin on your view and use the name `your_favourite_name` as your parameter. E.g

     `GET /users/?your_favourite_name={id, username}`

* Customize how it filter fields to include in a response.
    You can do this by inheriting DynamicFieldsMixin and override `list` and `retrieve` methods as shown below.

    ```python
    from django_restql.mixins import DynamicFieldsMixin

    class CustomDynamicFieldMixin(DynamicFieldsMixin):
        def list(self, request):
            # Your customization here
            return response

        def retrieve(self, request):
            # Your customization here
            return response
    ```
    **Note:** To be able to do this you must understand how **django-restql** is implemented, specifically **DynamicFieldsMixin** class, you can check it [here](https://github.com/yezyilomo/django-restql/blob/master/django_restql/mixins.py). In fact this is how **django-restql** is implemented(overriding `list` and `retrieve` methods of a view, nothing more and nothing less).

## Running Tests
`python setup.py test`

## Credits
This implementation is based on [dictfier](https://github.com/yezyilomo/dictfier) library and the idea behind GraphQL.

My intention is to extend the capability of [drf-dynamic-fields](https://github.com/dbrgn/drf-dynamic-fields) library to support more functionalities like allowing to query nested fields both flat and iterable.


## Contributing [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

We welcome all contributions. Please read our [CONTRIBUTING.md](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md) first. You can submit any ideas as [pull requests](https://github.com/yezyilomo/django-restql/pulls) or as [GitHub issues](https://github.com/yezyilomo/django-restql/issues). If you'd like to improve code, check out the [Code Style Guide](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md#styleguides) and have a good time!.
