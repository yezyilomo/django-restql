# Introduction
**Django RESTQL** is a python library which allows you to turn your API made with **Django REST Framework(DRF)** into a GraphQL like API. With **Django RESTQL**  you will be able to

* Send a query to your API and get exactly what you need, nothing more and nothing less.

* Control the data you get, not the server.

* Get predictable results, since you control what you get from the server.

* Get nested resources in a single request.

* Avoid Over-fetching and Under-fetching of data.

* Write(create & update) nested data of any level with flexibility.

Isn't it cool?.


# Requirements
* Python >= 3.5
* Django >= 1.11
* Django REST Framework >= 3.5


# Installing
```py
pip install django-restql
```


# Querying Data
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

A regular request returns all fields as specified on a DRF serializer, in fact **Django RESTQL** doesn't handle this request at all. Below is an example of regular request, as you see all fields are returned as specified on `UserSerializer`.

`GET /users`

```js
[
    {
        "id": 1,
        "username": "yezyilomo",
        "email": "yezileliilomo@hotmail.com",
    },
    ...
]
```

## Querying flat fields
**Django RESTQL** handle all GET requests with a `query` parameter, this parameter is the one used to pass all fields to be included/excluded in a response. For example to select `id` and `username` fields from User model, send a request with a ` query` parameter as shown below.

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

## Querying nested fields
**Django RESTQL** support querying both flat and nested resources, so you can expand or query nested fields at any level as defined on a serializer. In an example below we have `location` and `groups` as nested fields on User model.

```py
from rest_framework import serializers
from django.contrib.auth.models import User
from django_restql.mixins import DynamicFieldsMixin

from app.models import GroupSerializer, LocationSerializer


class GroupSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    class Meta:
        model = Group
        fields = ['id', 'name']


class LocationSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    class Meta:
        model = Location
        fields = ['id', 'country',  'city', 'street']


class UserSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    groups = GroupSerializer(many=True, read_only=True)
    location = LocationSerializer(many=False, read_only=True) 
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'location', 'groups']
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

### More examples to get you comfortable with the query syntax
`GET /users/?query={location, groups}`
```js
[
    {
        "location": {
            "id": 1,
            "contry": "Tanzania",
            "city": "Dar es salaam",
            "street": "Oyster Bay"
        }
        "groups": [
            {"id": 2, "name": "Auth_User"},
            {"id": 3, "name": "Admin_User"}
        ]
    },
    ...
]
```
<br/>

`GET /users/?query={id, username, groups{name}}`
```js
[
    {
        "id": 1,
        "username": "yezyilomo",
        "groups": [
            {"name": "Auth_User"},
            {"name": "Admin_User"}
        ]
    },
    ...
]
```

## Exclude(-) operator
When using **Django RESTQL** filtering as-is is great if there are no many fields on a serializer, but sometimes you might have a case where you would like everything except a handful of fields on a larger serializer. These fields might be nested and trying the whitelist approach is difficult or possibly too long for the url. **Django RESTQL** comes with the exclude(-) operator which can be used to exclude some fields in scenarios where you want to get all fields except few. Using exclude syntax is very simple,you just need to prepend the field to exclude with the exclude(-) operator when writing your query that's all. Take an example below

```py
from rest_framework import serializers 
from django_restql.mixins import DynamicFieldsMixin

from app.models import Location, Property


class LocationSerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "city", "country", "state", "street"]


class PropertySerializer(DynamicFieldsMixin, serializer.ModelSerializer):
    location = LocationSerializer(many=False, read_only=True) 
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location'
        ]
```

Get all location fields except `id` and `street`

`GET /location/?query={-id, -street}`
```js
[
    {
        "country": "China",
        "city": "Beijing",
        "state": "Chaoyang"
    },
    ...
]
```
This is equivalent to `query={country, city, state}`

You can use exclude operator on nested fields too, for example if you want to get `price` and `location` fields but under `location` you want all fields except `id` here is how you can do it.

`GET /property/?query={price, location{-id}}`
```js
[
    {
        "price": 5000
        "location": {
            "country": "China",
            "city" "Beijing",
            "state": "Chaoyang",
            "street": "Hanang"
        }
    },
    ...
]
```
This is equivalent to `query={price, location{country, city, state, street}}`

### More examples to get you comfortable with the exclude(-) operator syntax
Assuming this is the structure of the model we are querying
```py
data = {
    username,
    birthdate,
    location {
        country,
        city
    },
    contact {
        phone,
        email
    }
}
```

Here is how we can structure our query to exclude some fields using exclude(-) operator
```py
{-username}   ≡   {birthdate, location{country, city}, contact{phone, email}}

{-username, contact{phone}, location{country}}   ≡    {birthdate ,contact{phone}, location{country}}

{-contact, location{country}}   ≡    {username, birthdate, location{country}}

{-contact, -location}   ≡    {username, birthdate}

{username, location{-country}}   ≡    {username, location{city}}

{username, location{-city}, contact{-email}}   ≡    {username, location{country}, contact{phone}}
```

## Wildcard(*) operator
In addition to exclude(-) operator, **Django RESTQL** comes with a wildcard(\*) operator for including all fields. Just like exclude(-) operator using a wildcard(\*) operator is very simple, for example if you want to get all fields from a model you just need to do `query={*}`. This operator can be used to simplify some filtering which might endup being very long if done with other approaches. For example if you have a model with this format 

```py
user = {
    username,
    birthdate,
    contact {
        phone,
        email,
        twitter,
        github,
        linkedin,
        facebook
    }
}
```
Let's say you want to get all user fields but under `contact` field you want to get only `phone`, you could use the whitelisting approach as 

`query={username, birthdate, contact{phone}}` 

but if you have many fields on user model you might endup writing a very long query, so with `*` operator you can simply do `query={*, contact{phone}}` which means get me all fields on user model but under `contact` field I want only `phone` field, as you see the query is very short compared to the first one and it won't grow if more fields are added to the user model.

### More examples to get you comfortable with the wildcard(\*) operator syntax
```py
{*, -username, contact{phone}}   ≡   {birthdate, contact{phone}}

{username, contact{*, -facebook, -linkedin}}   ≡   {username, contact{phone, email, twitter, github}}

{*, -username, contact{*, -facebook, -linkedin}}   ≡   {birthdate, contact{phone, email, twitter, github}}
```


Below is a list of mistakes which leads to syntax error, these mistakes may happen accidentally as it's very easy/tempting to make them with the exclude(-) operator and wildcard(*) operator syntax.
```py
{username, -location{country}}  # Should not expand excluded field
{*username}  # What are you even trying to accomplish
{*location{country}}  # This is def wrong
{-username, birthdate}  # Should not whitelist and blacklist fields 
# at the same field level
```

**Note:** Any field level should either be whitelisting or blacklisting fields but not both.
<br/>


## DynamicSerializerMethodField
`DynamicSerializerMethodField` is a wraper of the `SerializerMethodField`, it adds a query argument from a parent serializer to a method bound to a `SerializerMethodField`, this query argument can be passed to a serializer used within a method to allow further querying. For example in the scenario below we are using `DynamicSerializerMethodField` because we want to be able to query `tomes` field.

```py
from django_restql.mixins import DynamicFieldsMixin
from django_restql.fields import DynamicSerializerMethodField


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    # Use `DynamicSerializerMethodField` instead of `SerializerMethodField`
    # if you want to be able to query `tomes`
    tomes = DynamicSerializerMethodField()
    class Meta:
        model = Course
        fields = ['name', 'code', 'tomes']

    def get_tomes(self, obj, query):
        # With `DynamicSerializerMethodField` you get this extra
        # `query` argument in addition to `obj`
        books = obj.books.all()

        # You can do what ever you want in here

        # `query` param and context are passed to BookSerializer to allow querying it
        serializer = BookSerializer(
            books,
            many=True, 
            query=query, 
            context=self.context
        )
        return serializer.data
```

`GET /course/?query={name, tomes}`
```js
[
    {
        "name": "Data Structures",
        "tomes": [
            {"title": "Advanced Data Structures", "author": "S.Mobit"},
            {"title": "Basic Data Structures", "author": "S.Mobit"}
        ]
    }
]
```
<br/>

`GET /course/?query={name, tomes{title}}`
```js
[
    {
        "name": "Data Structures",
        "tomes": [
            {"title": "Advanced Data Structures"},
            {"title": "Basic Data Structures"}
        ]
    }
]
```
<br/>

## DynamicFieldsMixin kwargs
`DynamicFieldsMixin` accepts extra kwargs in addition to those accepted by a serializer, these extra kwargs can be used to do more customizations on a serializer as explained below.

### fields kwarg
With **Django RESTQL** you can specify fields to be included when instantiating a serializer, this provides a way to refilter fields on nested fields(i.e you can opt to remove some fields on a nested field). Below is an example which shows how you can specify fields to be included on nested resources. 

```py
from rest_framework import serializers
from django.contrib.auth.models import User
from django_restql.mixins import DynamicFieldsMixin

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True, fields=["title"])
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']
```

`GET /courses/`
```js
[
    {
        "name": "Computer Programming",
        "code": "CS50",
        "books": [
            {"title": "Computer Programming Basics"},
            {"title": "Data structures"}
        ]
    },
    ...
]
```
As you see from the response above, the nested resource(book) has only one field(title) as specified on  `fields=["title"]` kwarg during instantiating BookSerializer, so if you send a request like 

`GET /course?query={name, code, books{title, author}}` 

you will get an error that `author` field is not found because it was not included on `fields=["title"]` kwarg.


### exclude kwarg
You can also specify fields to be excluded when instantiating a serializer by using `exclude` kwarg, below is an example which shows how to use `exclude` kwarg.
```py
from rest_framework import serializers
from django_restql.mixins import DynamicFieldsMixin

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True, exclude=["author"])
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']
```

`GET /courses/`
```js
[
    {
        "name": "Computer Programming",
        "code": "CS50",
        "books": [
            {"id": 1, "title": "Computer Programming Basics"},
            {"id": 2, "title": "Data structures"}
        ]
    },
    ...
]
```
From the response above you can see that `author` field has been excluded fom book nested resource as specified on  `exclude=["author"]` kwarg during instantiating BookSerializer.

**Note:** `fields` and `exclude` kwargs have no effect when you access the resources directly, so when you access books you will still get all fields i.e

`GET /books/`
```js
[
    {
        "id": 1,
        "title": "Computer Programming Basics",
        "author": "S.Mobit"
    },
    ...
]
```
So you can see that all fields have appeared as specified on `fields = ['id', 'title', 'author']` on BookSerializer class.
<br/>


### return_pk kwarg
With **Django RESTQL** you can specify whether to return nested resource pk or data. Below is an example which shows how we can use `return_pk` kwarg.

```py
from rest_framework import serializers
from django_restql.mixins import DynamicFieldsMixin

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True, return_pk=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']
```

`GET /course/`
```js
[
    {
        "name": "Computer Programming",
        "code": "CS50",
        "books": [1, 2]
    },
    ...
]
```
So you can see that on a nested field `books` pks have been returned instead of books data as specified on `return_pk=True` kwarg on `BookSerializer`.
<br/>


### disable_dynamic_fields kwarg
Sometimes there are cases where you want to disable fields filtering with on a specific nested field, **Django RESTQL** allows you to do so by using `disable_dynamic_fields` kwarg when instantiating a serializer. Below is an example which shows how to use `disable_dynamic_fields` kwarg.

```py
from rest_framework import serializers
from django_restql.mixins import DynamicFieldsMixin

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    # Disable fields filtering on this field
    books = BookSerializer(many=True, read_only=True, disable_dynamic_fields=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']
```

`GET /course/?query={name, books{title}}`
```js
[
    {
        "name": "Computer Programming",
        "books": [
            {"id": 1, "title": "Computer Programming Basics", "author": "J.Vough"},
            {"id": 2, "title": "Data structures", "author": "D.Denis"}
        ]
    },
    ...
]
```
So you can see that even though the query asked for only `title` field under `books`, all fields have been returned, so this means fields filtering has applied on `CourseSerializer` but not on `BookSerializer` because we used `disable_dynamic_fields=True` on it.
<br/>


## Query arguments
Just like GraphQL, Django RESTQL allows you to pass arguments on nested fields. These arguments can be used to do filtering, sorting and other stuffs that you like them to do. Below is a syntax for passing arguments

```
query = (age: 18){
    name,
    age,
    location(country: Canada, city: Toronto){
        country,
        city
    }
}
```
Here we have three arguments, `age`, `country` and `city` and their corresponding values.


### Filtering with query arguments
As mentioned before you can use query arguments to do filtering, Django RESTQL itself doesn't do filtering but you can intergrate it with [django-filter](https://github.com/carltongibson/django-filter) or [djangorestframework-filters](https://github.com/philipn/django-rest-framework-filters) to do the actual filtering, in this case Django RESTQL will be providing query arguments as filter parameters to these libraries.

To integrate with [django-filter](https://github.com/carltongibson/django-filter) edit your `settings.py` file as shown below
```py
# settings.py
REST_FRAMEWORK = {
    # This is needed to be able to get filter parameters from query arguments
    'DEFAULT_FILTER_BACKEND': 'django_restql.filters.RESTQLFilterBackend'
}

RESTQL = {
    # This tells django-restql which filter backend to use(send generated filter parameters to)
    'DEFAULT_BASE_FILTER_BACKEND': 'django_filters.rest_framework.DjangoFilterBackend'
}
```

And for [djangorestframework-filters](https://github.com/philipn/django-rest-framework-filters)
```py
# settings.py
REST_FRAMEWORK = {
    # This is needed to be able to get filter parameters from query arguments
    'DEFAULT_FILTER_BACKEND': 'django_restql.filters.RESTQLFilterBackend'
}

RESTQL = {
    # This tells django-restql which filter backend to use(send generated filter parameters to)
    'DEFAULT_BASE_FILTER_BACKEND': 'rest_framework_filters.backends.RestFrameworkFilterBackend'
}
```

Once configured, you can continue to use all of the features found in [django-filter](https://github.com/carltongibson/django-filter) or [djangorestframework-filters](https://github.com/philipn/django-rest-framework-filters) as usual. The purpose of Django RESTQL on filtering is only to generate filter parameters form query arguments, for example if you have a query like
```
query = (age: 18){
    name,
    age,
    location(country: Canada, city: Toronto){
        country,
        city
    }
}
```

Django RESTQL would generate three filter parameters from this as shown below and send them to `DEFAULT_BASE_FILTER_BACKEND` set for it to do the filtering.
```py
filter_params = {"age": 18, "location__country": "Canada", "location__city": "Toronto"}
```

If those two libraries doesn't satisfy your needs on filtering, you can write your own filter backend or extend one of those provided by these two libraries and set it on `DEFAULT_BASE_FILTER_BACKEND`.


## Setting up eager loading
Often times, using `prefetch_related` or `select_related` on a view queryset can help speed up the serialization. For example, if you had a many-to-many relation like Books to a Course, it's usually more efficient to call `prefetch_related` on the books so that serializing a list of courses only triggers one additional query, instead of a number of queries equal to the number of courses.

`EagerLoadingMixin` gives access to `prefetch_related` and `select_related` properties, these two are dictionaries that match serializer field names to respective values that would be passed into `prefetch_related` or `select_related`. Take the following serializers as examples.

```py
class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['name', 'code', 'books']

class StudentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    program = CourseSerializer(source="course", many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['name', 'age', 'program', 'phone_numbers']
```

In a view, these can be used as described earlier in this documentation. However, if prefetching of `books` always happened, but we did not ask for `{program}` or `program{books}`, then we did an additional query for nothing. Conversely, not prefetching can lead to even more queries being triggered. When leveraging the `EagerLoadingMixin` on a view, the specific fields that warrant a `select_related` or `prefetch_related` can be described.


### Syntax for prefetch_related and select_related
The format of syntax for `select_related` and  `prefetch_related` is as follows

```py
select_related = {"serializer_field_name": ["field_to_select"]}
prefetch_related = {"serializer_field_name": ["field_to_prefetch"]}
```

If you are selecting or prefetching one field per serializer field name you can use
```py
select_related = {"serializer_field_name": "field_to_select"}
prefetch_related = {"serializer_field_name": "field_to_prefetch"}
```

**Syntax Interpretation**

* `serializer_field_name` stands for the name of the field to prefetch or select(as named on a serializer).
* `fields_to_select` stands for argument(s) to pass when calling `select_related` method.
* `fields_to_prefetch` stands for arguments(s) to pass when calling `prefetch_related` method. This can be a string or `Prefetch` object.
* If you want to select or prefetch nested field use dot(.) to separate parent and child fields on `serializer_field_name` eg `parent.child`.


### Example of EagerLoadingMixin usage

```py
from rest_framework import viewsets
from django_restql.mixins import EagerLoadingMixin
from myapp.serializers import StudentSerializer
from myapp.models import Student

class StudentViewSet(EagerLoadingMixin, viewsets.ModelViewSet):
	serializer_class = StudentSerializer
	queryset = Student.objects.all()

    # The Interpretation of this is 
    # Select `course` only if program field is included in a query
    select_related = {
		"program": "course"
	}

    # The Interpretation of this is 
    # Prefetch `course__books` only if program or program.books 
    # fields are included in a query
	prefetch_related = {
		"program.books": "course__books"
	}
```

### Example Queries

- `{name}`:  &nbsp;&nbsp; Neither `select_related` or `prefetch_related` will be run since neither field is present on the serializer for this query.

- `{program}`: &nbsp;&nbsp; Both `select_related` and `prefetch_related` will be run, since `program` is present in it's entirety (including the `books` field).

- `{program{name}}`: &nbsp;&nbsp; Only `select_related` will be run, since `books` are not present on the program fields.

- `{program{books}}`: &nbsp;&nbsp; Both will be run here as well, since this explicitly fetches books.

### More example to get you comfortable with the syntax
Assuming this is the structure of the model and corresponding field types 

```py
user = {
    username,        # string
    birthdate,       # string
    location {       # foreign key related field
        country,     # string
        city         # string
    },
    contact {        # foreign key related field
        email,       # string
        phone {      # foreign key related field
            number,  # string
            type     # string
        }
    }
    articles {       # many related field
        title,       # string
        body,        # text
        reviewers {  # many related field
            name,    # string
            rating   # number
        }
    }
}
```

Here is how `select_related` and `prefetch_related` could be written for this model
```py
select_related = {
    "location": "location",
    "contact": "contact",
    "contact.phone": "contact__phone"
}

prefetch_related = {
    "articles": Prefetch("articles", queryset=Article.objects.all()),
    "articles.reviews": "articles__reviewers"
}
```

### Known Caveats
When prefetching with a `to_attr`, ensure that there are no collisions. Django does not allow multiple prefetches with the same `to_attr` on the same queryset.

When prefetching *and* calling `select_related` on a field, Django may error, since the ORM does allow prefetching a selectable field, but not both at the same time.

## Settings
Configuration for **Django RESTQL** is all namespaced inside a single Django setting named `RESTQL`, below is a list of what you can configure under `RESTQL` setting.

### QUERY_PARAM_NAME
The default value for this is `query`. If you don't want to use the name `query` as your parameter, you can change it with`QUERY_PARAM_NAME` on settings file e.g 
```py
RESTQL = {
    'QUERY_PARAM_NAME': 'your_favourite_name'
}
```
Now you can use the name `your_favourite_name` as your query parameter. E.g
 
`GET /users/?your_favourite_name={id, username}`

### DEFAULT_BASE_FILTER_BACKEND
The default value for this is `object`.
This is used if you want to use query arguments to do filtering, this is discussed in detail on [Filtering with query arguments](#filtering-with-query-arguments)

### AUTO_APPLY_EAGER_LOADING
The default value for this is `True`. When using the `EagerLoadingMixin`, this setting controls if the mappings for `select_related` and `prefetch_related` are applied automatically when calling `get_queryset`. To turn it off, set the `AUTO_APPLY_EAGER_LOADING` setting or `auto_apply_eager_loading` attribute on the view to `False`. 
```py
# settings.py file
# This will turn off auto apply eager loading globally
RESTQL = {
    'AUTO_APPLY_EAGER_LOADING': False
}
```

If auto apply eager loading is turned off, the method `apply_eager_loading` can still be used on your queryset if you wish to select or prefetch related fields according to your conditions, For example you can check if there was a query parameter passed in by using `has_restql_query_param`, if true then apply eager loading otherwise return a normal queryset.
```py
from rest_framework import viewsets
from django_restql.mixins import EagerLoadingMixin
from myapp.serializers import StudentSerializer
from myapp.models import Student

class StudentViewSet(EagerLoadingMixin, viewsets.ModelViewSet):
	serializer_class = StudentSerializer
	queryset = Student.objects.all()

    # Turn off auto apply eager loading per view
    # This overrides the `AUTO_APPLY_EAGER_LOADING` setting on this view
    auto_apply_eager_loading = False
    select_related = {
		"program": "course"
	}
	prefetch_related = {
		"program.books": "course__books"
	}
	
	def get_queryset(self):
	    queryset = super().get_queryset()
	    if self.has_restql_query_param:
	        queryset = self.apply_eager_loading(queryset)
        return queryset
```


# Mutating Data
**Django RESTQL** got your back on creating and updating nested data too, it has two components for mutating nested data, `NestedModelSerializer` and `NestedField`. A serializer `NestedModelSerializer` has `update` and `create` logics for nested fields on the other hand `NestedField` is used to validate data before calling `update` or `create` method.


## Using NestedField and NestedModelSerializer
Just like in querying data, mutating nested data with **Django RESTQL** is very simple, you just have to inherit `NestedModelSerializer` on a serializer with nested fields and use `NestedField` to define those nested fields. Below is an example which shows how to use `NestedModelSerializer` and `NestedField`.
```py
from rest_framework import serializers
from django_restql.serializers import NestedModelSerializer
from django_restql.fields import NestedField

from app.models import Location, Amenity, Property


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "city", "country"]


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name"]
        

# Inherit NestedModelSerializer to support create and update 
# on nested fields
class PropertySerializer(NestedModelSerializer):
    # Define location as nested field
    location = NestedField(LocationSerializer)

    # Define amenities as nested field
    amenities = NestedField(AmenitySerializer, many=True)
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location', 'amenities'
        ]
```
<br>


```POST /api/property/```

Request Body
```js
{
    "price": 60000,
    "location": {
        "city": "Newyork",
        "country": "USA"
    },
    "amenities": {
        "add": [3],
        "create": [
            {"name": "Watererr"},
            {"name": "Electricity"}
        ]
    }
}
```
What's done here is pretty clear, location will be created and associated with the property created, also create operation on amenities will create amenities with values specified in a list and associate with the property, add operation will add amenity with id 4 to a list of amenities of the property.

**Note:** POST for many related field supports two operations which are `create` and `add`.

Response
```js
{
    "id": 2,
    "price": 60000,
    "location": {
        "id": 3,
        "city": "Newyork",
        "country": "USA"
    },
    "amenities": [
        {"id": 1, "name": "Watererr"},
        {"id": 2, "name": "Electricity"},
        {"id": 3, "name": "Swimming Pool"}
    ]
}
```
<br>


```PUT /api/property/2/```

Request Body
```js
{
    "price": 50000,
    "location": {
        "city": "Newyork",
        "country": "USA"
    },
    "amenities": {
        "add": [4],
        "create": [{"name": "Fance"}],
        "remove": [3],
        "update": {1: {"name": "Water"}}
    }
}
```
**Note:** Here `add`, `create`, `remove` and `update` are operations, so `add` operation add amenitiy with id 4 to a list of amenities of the property, `create` operation create amenities with values specified in a list, `remove` operation dessociate amenities with id 3 from a property, `update` operation edit amenity with id 1 according to values specified.

**Note:** PUT/PATCH for many related field supports four operations which are `create`, `add`, `remove` and `update`.

Response
```js
{
    "id": 2,
    "price": 50000,
    "location": {
        "id": 3,
        "city": "Newyork",
        "country": "USA"
    },
    "amenities": [
        {"id": 1, "name": "Water"},
        {"id": 2, "name": "Electricity"},
        {"id": 4, "name": "Bathtub"},
        {"id": 5, "name": "Fance"}
    ]
}
```
<br>


## Using NestedField with accept_pk kwarg.
`accept_pk=True` is used if you want to update nested field by using pk/id of existing data(basically associate and dessociate existing nested resources with the parent resource without actually mutating the nested resource). This applies to ForeignKey relation only.

```py
from rest_framework import serializers 
from django_restql.fields import NestedField
from django_restql.serializers import NestedModelSerializer

from app.models import Location, Property


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "city", "country"]


class PropertySerializer(NestedModelSerializer):
    # pk based nested field
    location = NestedField(LocationSerializer, accept_pk=True)
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location'
        ]
```
<br>


```POST /api/property/```

Request Body
```js
{
    "price": 40000,
    "location": 2
}
```
**Note:** Here location resource with id 2 is already existing, so what's done here is create new property resource and associate it with a location with id 2.
<br>

Response
```js
{
    "id": 1,
    "price": 40000,
    "location": {
        "id": 2,
        "city": "Tokyo",
        "country": "China"
    }
}
```
<br>


## Using NestedField with create_ops and update_ops kwargs.
You can restrict some operations by using `create_ops` and `update_ops` keyword arguments as follows

```py
from rest_framework import serializers 
from django_restql.fields import NestedField
from django_restql.serializers import NestedModelSerializer 

from app.models import Location, Amenity, Property


class AmenitySerializer(serializers.ModelSerializer):
    class Meta:
        model = Amenity
        fields = ["id", "name"]
        

class PropertySerializer(NestedModelSerializer):
    amenities = NestedField(
        AmenitySerializer, 
        many=True,
        create_ops=["add"],  # Allow only add operation
        update_ops=["add", "remove"]  # Allow only add and remove operations
    )
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'amenities'
        ]
```
<br>


```POST /api/property/```

Request Body
```js
{
    "price": 60000,
    "amenities": {
        "add": [1, 2]
    }
}
```
**Note:** According to `create_ops=["add"]`, you can't use `create` operation in here!.
<br>

Response
```js
{
    "id": 2,
    "price": 60000,
    "amenities": [
        {"id": 1, "name": "Watererr"},
        {"id": 2, "name": "Electricity"}
    ]
}
```
<br>


```PUT /api/property/2/```

Request Body
```js
{
    "price": 50000,
    "amenities": {
        "add": [3],
        "remove": [2]
    }
}
```
**Note:** According to `update_ops=["add", "remove"]`, you can't use `create` or `update` operation in here!.
<br>

Response
```js
{
    "id": 2,
    "price": 50000,
    "amenities": [
        {"id": 1, "name": "Water"},
        {"id": 3, "name": "Bathtub"}
    ]
}
```
<br>


## Using DynamicFieldsMixin and NestedField together
You can use `DynamicFieldsMixin` and `NestedModelSerializer` together if you want your serializer to be writable(on nested fields) and support querying data, this is very common. Below is an example which shows how you can use `DynamicFieldsMixin` and `NestedField` together.
```py
from rest_framework import serializers 
from django_restql.fields import NestedField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer 

from app.models import Location, Property


class LocationSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "city", "country"]

# Inherit both DynamicFieldsMixin and NestedModelSerializer
class PropertySerializer(DynamicFieldsMixin, NestedModelSerializer):
    location = NestedField(LocationSerializer)
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location'
        ]
```

`NestedField` is nothing but a serializer wrapper, it returns an instance of a modified version of a serializer passed, so you can pass all the args and kwargs accepted by a serializer on it, it will simply pass them to a serializer passed when instantiating an instance. So you can pass anything accepted by a serializer to a `NestedField` wrapper, and if a serializer passed inherits `DynamicFieldsMini` just like `LocationSerializer` on above example then you can pass any arg or kwarg accepted by `DynamicFieldsMixin` when defining location as a nested field, i.e

```py
location = NestedField(LocationSerializer, fields=[...])
```

```py 
location = NestedField(LocationSerializer, exclude=[...])
``` 

```py
location = NestedField(LocationSerializer, return_pk=True)
``` 
