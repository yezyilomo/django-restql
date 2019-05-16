# django-restql

[![Latest Version](https://img.shields.io/pypi/v/django-restql.svg)](https://pypi.org/project/django-restql/)
[![Python Versions](https://img.shields.io/pypi/pyversions/django-restql.svg)](https://pypi.org/project/django-restql/)
[![License](https://img.shields.io/pypi/l/django-restql.svg)](https://pypi.org/project/django-restql/)

**django-restql** is a python library which allows django-rest-framework to dynamically select only a subset of fields per DRF resource(Support both flat and nested resources)

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
from django_restql.mixins import DynamicFieldsMixin

class UserViewSet(DynamicFieldsMixin, viewsets.ModelViewSet):
    queryset = User.objects.all().order_by('-date_joined')
    serializer_class = UserSerializer
```

A regular request returns all fields specified on DRF serializer, in fact **django-restql** doesn't handle this request at all:

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

**django-restql** handle all GET requests with ```query``` parameter, this parameter is the one used to pass all fields to be included on a response. For example to select ```id``` and ```username``` fields from ```user``` model, send a request with a ``` query``` parameter as shown below.

```GET /users/?query=[["id", "username"]]```

```json
    [
      {
        "id": 1,
        "username": "yezyilomo"
      },
      ...
    ]
```

If a query contains nested field, **django-restql** will return its id or array of ids for the case of nested iterable field(one2many or many2many). For example on a request below ```location``` is a flat nested field(many2one) and ```groups``` is an iterable nested field(one2many or many2many).

```GET /users/?query=[["id", "username", "location", "groups"]]```

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

With **django-restql** you can expand or query nested fields at any level. For example you can query a country and region field from location.

```GET /users/?query=[["id", "username", {"location": ["country", "region"]}]]```

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

**django-restql** got your back on expanding or querying iterable nested fields too. For example if you want to expand ```groups``` field into ``` id``` and ```name```, here is how you would do it.

```GET /users/?query=[["id", "username" {"groups": [[ "id", "name" ]]}]]```

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

**Note:**

The notation used to expand flat nested fields is  ```field_name=[sub_field1, sub_field2, ...]```

And for iterable nested fields  ```field_name=[[sub_field1, sub_field2, ...]]```

For more information on how to create queries you can refer to [dictfier](https://github.com/yezyilomo/dictfier#how-dictfier-works) which is a library used to implement this project.

## Customizing django-restql
**django-restql**  is very configurable, here is what you can customize
* Change the name of ```query``` parameter.

    If you don't want to use the name ```query``` as your parameter, you can inherit ```DynamicFieldsMixin``` and change it as shown below
    ```python
    from django_restql.mixins import DynamicFieldsMixin

    class MyDynamicFieldMixin(DynamicFieldsMixin):
        query_param_name = "your_favourite_name"
     ```
     Now you can use this Mixin on your serializers and use the name ```your_favourite_name``` as your parameter. E.g

     ```GET /users/?your_favourite_name=[["id", "username"]]```


## Credits
This implementation is based on [dictfier](https://github.com/yezyilomo/dictfier) library and the idea behind GraphQL.

My intention is to extend the capability of [drf-dynamic-fields](https://github.com/dbrgn/drf-dynamic-fields) library to support more functionalities like allowing to query nested fields both flat and iterable.


## Contributing [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

We welcome all contributions. Please read our [CONTRIBUTING.md](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md) first. You can submit any ideas as [pull requests](https://github.com/yezyilomo/django-restql/pulls) or as [GitHub issues](https://github.com/yezyilomo/django-restql/issues). If you'd like to improve code, check out the [Code Style Guide](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md#styleguides) and have a good time!.
