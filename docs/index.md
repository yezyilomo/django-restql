# Introduction

**Django RESTQL** is a python library which allows you to turn your API made with **Django REST Framework(DRF)** into a GraphQL like API. With **Django RESTQL**  you will be able to

* Send a query to your API and get exactly what you need, nothing more and nothing less.

* Control the data you get, not the server.

* Get predictable results, since you control what you get from the server.

* Get nested resources in a single request.

* Avoid Over-fetching and Under-fetching of data.

* Write(create & update) nested data of any level in a single request.

Isn't it cool?.


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

**Django RESTQL** support querying both flat and nested resources, you can expand or query nested fields at any level as defined on a serializer. It also supports querying with all HTTP methods i.e (GET, POST, PUT & PATCH)

You can do a lot with **Django RESTQL** apart from querying data, like

- Rename fields
- Restrict some fields on nested fields
- Optimize data fetching on nested fields
- Data filtering and pagination by using query arguments
- Data mutation(Create and update nested data of any level in a single request)


## Django RESTQL Play Ground
[**Django RESTQL Play Ground**](https://django-restql-playground.yezyilomo.me) is a graphical, interactive, in-browser tool which you can use to test **Django RESTQL** features like data querying, mutations etc to get the idea of how the library works before installing it. It's more like a [**live demo**](https://django-restql-playground.yezyilomo.me) for **Django RESTQL**, it's available at [https://django-restql-playground.yezyilomo.me](https://django-restql-playground.yezyilomo.me)
