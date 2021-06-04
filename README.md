# <img height="24" src="https://raw.githubusercontent.com/yezyilomo/django-restql/master/docs/img/icon.svg" /> [  Django RESTQL](https://yezyilomo.github.io/django-restql)

[![Build Status](https://api.travis-ci.com/yezyilomo/django-restql.svg?branch=master)](https://api.travis-ci.com/yezyilomo/django-restql) 
[![Latest Version](https://img.shields.io/pypi/v/django-restql.svg)](https://pypi.org/project/django-restql/) 
[![Python Versions](https://img.shields.io/pypi/pyversions/django-restql.svg)](https://pypi.org/project/django-restql/) 
[![License](https://img.shields.io/pypi/l/django-restql.svg)](https://pypi.org/project/django-restql/)
&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp; 
[![Downloads](https://pepy.tech/badge/django-restql)](https://pepy.tech/project/django-restql) 
[![Downloads](https://pepy.tech/badge/django-restql/month)](https://pepy.tech/project/django-restql) 
[![Downloads](https://pepy.tech/badge/django-restql/week)](https://pepy.tech/project/django-restql)


**Django RESTQL** is a python library which allows you to turn your API made with **Django REST Framework(DRF)** into a GraphQL like API. With **Django RESTQL** you will be able to

* Send a query to your API and get exactly what you need, nothing more and nothing less.

* Control the data you get, not the server.

* Get predictable results, since you control what you get from the server.

* Get nested resources in a single request.

* Avoid Over-fetching and Under-fetching of data.

* Write(create & update) nested data of any level in a single request.

Isn't it cool?.

Want to see how this library is making all that possible? 

Check out the full documentation at [https://yezyilomo.github.io/django-restql](https://yezyilomo.github.io/django-restql)

Or try a live demo on [Django RESTQL Playground](https://django-restql-playground.yezyilomo.me)


## Requirements
* Python >= 3.5
* Django >= 1.11
* Django REST Framework >= 3.5


## Installing
```py
pip install django-restql
```


## Getting Started
Using **Django RESTQL** to query data is very simple, you just have to inherit the `DynamicFieldsMixin` class when defining a serializer that's all.
```py
from rest_framework import serializers
from django.contrib.auth.models import User
from django_restql.mixins import DynamicFieldsMixin


class UserSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
```

**Django RESTQL** handle all requests with a `query` parameter, this parameter is the one used to pass all fields to be included/excluded in a response. For example to select `id` and `username` fields from User model, send a request with a ` query` parameter as shown below.

`GET /users/?query={id, username}`
```js
[
    {
        "id": 1,
        "username": "yezyilomo"
    },
    ...
]
```

**Django RESTQL** support querying both flat and nested resources, so you can expand or query nested fields at any level as defined on a serializer. In an example below we have `location` as a nested field on User model.

```py
from rest_framework import serializers
from django.contrib.auth.models import User
from django_restql.mixins import DynamicFieldsMixin

from app.models import GroupSerializer, LocationSerializer


class LocationSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'country',  'city', 'street']


class UserSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    location = LocationSerializer(many=False, read_only=True) 
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'location']
```

If you want only `country` and `city` fields on a `location` field when retrieving users here is how you can do it

`GET /users/?query={id, username, location{country, city}}`
```js
[
    {
        "id": 1,
        "username": "yezyilomo",
        "location": {
            "contry": "Tanzania",
            "city": "Dar es salaam"
        }
    },
    ...
]
```

You can even rename your fields when querying data, In an example below the field `location` is renamed to `address`

`GET /users/?query={id, username, address: location{country, city}}`
```js
[
    {
        "id": 1,
        "username": "yezyilomo",
        "address": {
            "contry": "Tanzania",
            "city": "Dar es salaam"
        }
    },
    ...
]
```


## [Documentation :pencil:](https://yezyilomo.github.io/django-restql)
You can do a lot with **Django RESTQL** apart from querying data, like
- Rename fields
- Restrict some fields on nested fields
- Optimize data fetching on nested fields
- Data filtering and pagination by using query arguments
- Data mutation(Create and update nested data of any level in a single request)

Full documentation for this project is available at [https://yezyilomo.github.io/django-restql](https://yezyilomo.github.io/django-restql), you are encouraged to read it inorder to utilize this library to the fullest.


## [Django RESTQL Play Ground](https://django-restql-playground.yezyilomo.me)
[**Django RESTQL Play Ground**](https://django-restql-playground.yezyilomo.me) is a graphical, interactive, in-browser tool which you can use to test **Django RESTQL** features like data querying, mutations etc to get the idea of how the library works before installing it. It's more like a [**live demo**](https://django-restql-playground.yezyilomo.me) for **Django RESTQL**, it's available at [https://django-restql-playground.yezyilomo.me](https://django-restql-playground.yezyilomo.me)


## Running Tests
`python runtests.py`


## Credits
* Implementation of this library is based on the idea behind [GraphQL](https://graphql.org/).
* My intention is to extend the capability of [drf-dynamic-fields](https://github.com/dbrgn/drf-dynamic-fields) library to support more functionalities like allowing to query nested fields both flat and iterable at any level and allow writing on nested fields while maintaining simplicity.


## Contributing [![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg?style=flat-square)](http://makeapullrequest.com)

We welcome all contributions. Please read our [CONTRIBUTING.md](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md) first. You can submit any ideas as [pull requests](https://github.com/yezyilomo/django-restql/pulls) or as [GitHub issues](https://github.com/yezyilomo/django-restql/issues). If you'd like to improve code, check out the [Code Style Guide](https://github.com/yezyilomo/django-restql/blob/master/CONTRIBUTING.md#styleguides) and have a good time!.
