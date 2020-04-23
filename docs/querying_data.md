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

<h3>More examples to get you comfortable with the query syntax</h3>
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

<h3>More examples to get you comfortable with the exclude(-) operator syntax</h3>
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

<h3>More examples to get you comfortable with the wildcard(*) operator syntax</h3>
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

<h3>Example Queries</h3>

- `{name}`:  &nbsp;&nbsp; Neither `select_related` or `prefetch_related` will be run since neither field is present on the serializer for this query.

- `{program}`: &nbsp;&nbsp; Both `select_related` and `prefetch_related` will be run, since `program` is present in it's entirety (including the `books` field).

- `{program{name}}`: &nbsp;&nbsp; Only `select_related` will be run, since `books` are not present on the program fields.

- `{program{books}}`: &nbsp;&nbsp; Both will be run here as well, since this explicitly fetches books.

<h3>More example to get you comfortable with the syntax</h3>
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