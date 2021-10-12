# Mutating Data
**Django RESTQL** got your back on creating and updating nested data too, it has two components for mutating nested data, `NestedModelSerializer` and `NestedField`. A serializer `NestedModelSerializer` has `update` and `create` logics for nested fields on the other hand `NestedField` is used to validate data before calling `update` or `create` method.


## Using NestedField and NestedModelSerializer
Just like in querying data, mutating nested data with **Django RESTQL** is very simple, you just have to inherit `NestedModelSerializer` on a serializer with nested fields and use `NestedField` to define those nested fields which you want to be able to mutate. Below is an example which shows how to use `NestedModelSerializer` and `NestedField`.
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

With serializers defined as shown above, you will be able to send data mutation request like

```POST /api/property/```

With a request body like
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

And get a response as
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

Just to clarify what happed here:

- location has been created and associated with the property created
- `create` operation has created amenities with values specified in a list and associate them with the property
- `add` operation has added amenity with id=3 to a list of amenities of the property.

!!! note
    POST for many related fields supports two operations which are `create` and `add`.
<br>

Below we have an example where we are trying to update the property we have created in the previous example.

```PUT/PATCH /api/property/2/```

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

After sending the requst above we'll get a response which looks like

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

From the request body `add`, `create`, `remove` and `update` are operations

What you see in the response above are details of our property, what really happened after sending the update request is

- `add` operation added amenitiy with id=4 to a list of amenities of the property
- `create` operation created amenities with values specified in a list
- `remove` operation removed amenities with id=3 from a property
- `update` operation updated amenity with id=1 according to values specified.


!!! note
    PUT/PATCH for many related fields supports four operations which are `create`, `add`, `remove` and `update`.


## Self referencing nested field
Currently DRF doesn't allow declaring self referencing nested fields but you might have a self referencing nested field in your project since Django allows creating them. Django RESTQL comes with a nice way to deal with this scenario.

Let's assume we have a student model as shows below

```py
# models.py

class Student(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    study_partners = models.ManyToManyField('self', related_name='study_partners')
```

As you can see from the model above `study_partners` is a self referencing field. Below is the corresponding serializer for our model

```py
# serializers.py

class StudentSerializer(NestedModelSerializer):
    # Define study_partners as self referencing nested field
    study_partners = NestedField(
        'self',
        many=True,
        required=False,
        exclude=['study_partners']
    )

    class Meta:
        model = Student
        fields = ['id', 'name', 'age', 'study_partners']
```

You can see that we have passed `self` to `NestedField` just like in `Student` model, this means that `study_partners` field is a self referencing field.

The other important thing here is `exclude=['study_partners']`, this excludes the field `study_partners` on a nested field to avoid recursion error if the self reference is cyclic.


## NestedField kwargs
`NestedField` accepts extra kwargs in addition to those accepted by a serializer, these extra kwargs can be used to do more customizations on a nested field as explained below.


### accept_pk kwarg
`accept_pk=True` is used if you want to be able to update nested field by using pk/id of existing data(basically associate existing nested resource with the parent resource). This applies to foreign key relations only. The default value for `accept_pk` is `False`.

Below is an example showing how to use `accept_pk` kwarg.

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

Now sending mutation request as


```POST /api/property/```

Request Body
```js
{
    "price": 40000,
    "location": 2
}
```
!!! note
    Here location resource with id=2 exists already, so what's done here is create a new property resource and associate it with this location whose id is 2.

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

Using `accept_pk` doesn't limit you from sending data(instead of pk to nested resource), setting `accept_pk=True` means you can send both data and pks. For instance from the above example you could still do 

```POST /api/property/```

Request Body
```js
{
    "price": 63000,
    "location": {
        "city": "Dodoma",
        "country": "Tanzania"
    }
}
```

Response
```js
{
    "id": 2,
    "price": 63000,
    "location": {
        "id": 3,
        "city": "Dodoma",
        "country": "Tanzania"
    }
}
```


### accept_pk_only kwarg
`accept_pk_only=True` is used if you want to be able to update nested field by using pk/id only. This applies to foreign key relations only as well. The default value for `accept_pk_only` kwarg is `False`, if `accept_pk_only=True` is set you won't be able to send data to create a nested resource.

Below is an example showing how to use `accept_pk_only` kwarg.
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
    location = NestedField(LocationSerializer, accept_pk_only=True)
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location'
        ]
```

Sending mutation request

```POST /api/property/```

Request Body
```js
{
    "price": 40000,
    "location": 2  // You can't send data in here, you can only send pk/id
}
```

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

!!! note
    By default `accept_pk=False` and `accept_pk_only=False`, so nested field(foreign key related) accepts data only by default, if `accept_pk=True` is set, it accepts data and pk/id, and if `accept_pk_only=True` is set it accepts pk/id only. You can't set both `accept_pk=True` and `accept_pk_only=True`.


### create_ops and update_ops kwargs.
These two kwargs are used to restrict some operations when creating or updating nested data. Below is an example showing how to restrict some operations by using these two kwargs.

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

Sending create mutation request

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
!!! note
    Since `create_ops=["add"]`, you can't use `create` operation in here!.

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

Sending update mutation request

```PUT/PATCH /api/property/2/```

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
!!! note
    Since `update_ops=["add", "remove"]`, you can't use `create` or `update` operation in here!.

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


### allow_remove_all kwarg
This kwarg is used to enable and disable removing all related objects on many related nested field at once by using `__all__` directive. The default value of `allow_remove_all` is `False`, which means removing all related objects on many related nested fields is disabled by default so if you want to enable it you must set its value to `True`. For example 

```py
class CourseSerializer(NestedModelSerializer):
    books = NestedField(BookSerializer, many=True, allow_remove_all=True)

    class Meta:
        model = Course
        fields = ["name", "code", "books"]
```

With `allow_remove_all=True` as set above you will be able to send a request like

```PUT/PATCH /courses/3/```

Request Body
```js
{
    "books": {
        "remove":  "__all__"
    }
}
```

This will remove all books associated with a course being updated.
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

`NestedField` is nothing but a serializer wrapper, it returns an instance of a modified version of a serializer passed, so you can pass all the args and kwargs accepted by a serializer on it, it will simply pass them along to a serializer passed when instantiating an instance. So you can pass anything accepted by a serializer to a `NestedField` wrapper, and if a serializer passed inherits `DynamicFieldsMixin` just like `LocationSerializer` on the example above then you can pass any arg or kwarg accepted by `DynamicFieldsMixin` when defining location as a nested field, i.e

```py
location = NestedField(LocationSerializer, fields=[...])
```

```py 
location = NestedField(LocationSerializer, exclude=[...])
``` 

```py
location = NestedField(LocationSerializer, return_pk=True)
``` 


!!! note
    If you want to use `required=False` kwarg on `NestedField` you might want to include `allow_null=True` too if you want your nested field to be set to `null` if you haven't supplied it. For example 


```py
from rest_framework import serializers 
from django_restql.fields import NestedField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer 

from app.models import Location, Property


class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = ["id", "city", "country"]


class PropertySerializer(NestedModelSerializer):
    # Passing both `required=False` and `allow_null=True`
    location = NestedField(LocationSerializer, required=False, allow_null=True)
    class Meta:
        model = Property
        fields = [
            'id', 'price', 'location'
        ]
```

The `required=False` kwarg allows you to create Property without including `location` field and the `allow_null=True` kwarg allows `location` field to be set to null if you haven't supplied it. For example

Sending mutation request

```POST /api/property/```

Request Body
```js
{
    "price": 40000
    // You can see that the location is not included here
}
```

Response
```js
{
    "id": 2,
    "price": 50000,
    "location": null  // This is the result of not including location
}
```

If you use `required=False` only without `allow_null=True`, The serializer will allow you to create Property without including `location` field but it will throw error because by default `allow_null=False` which means `null`/`None`(which is what's passed when you don't supply `location` value) is not considered a valid value.


## Working with data mutation without request
**Django RESTQL** allows you to do data mutation without having request object, this is used if you don't want to get your mutation data input(serializer data) from a request, in fact `NestedModelSerializer` and `NestedFied` can work independently without using request. Below is an example showing how you can work with data mutation without request object.

```py
from rest_framework import serializers
from django_restql.fields import NestedField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, NestedModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, NestedModelSerializer):
    books = NestedField(BookSerializer, many=True, required=False)
    class Meta:
        model = Course
        fields = ['id', 'name', 'code', 'books']
```

From serializers above you can create a course like

```py
data = {
    "name": "Computer Programming",
    "code": "CS50",
    "books": {
        "add": [1, 2],
        "create": [
            {'title': 'Basic Data Structures', 'author': 'J. Davis'},
            {'title': 'Advanced Data Structures', 'author': 'S. Mobit'}
        ]
    }
}

serializer = CourseSerializer(data=data)
serializer.is_valid()
serializer.save()

print(serializer.data)

# This will print
{
    "id": 2,
    "name": "Computer Programming",
    "code": "CS50",
    "books": [
        {'id': 1, 'title': 'Programming Intro', 'author': 'K. Moses'},
        {'id': 2, 'title': 'Understanding Computers', 'author': 'B. Gibson'},
        {'id': 3, 'title': 'Basic Data Structures', 'author': 'J. Davis'},
        {'id': 4, 'title': 'Advanced Data Structures', 'author': 'S. Mobit'}
    ]
}
```

To update a created course you can do it like

```py
data = {
    "code": "CS100",
    "books": {
        "remove": [2, 3]
    }
}

course_obj = Course.objects.get(pk=2)

serializer = CourseSerializer(course_obj, data=data)
serializer.is_valid()
serializer.save()

print(serializer.data)

# This will print
{
    "id": 2,
    "name": "Computer Programming",
    "code": "CS100",
    "books": [
        {'id': 1, 'title': 'Programming Intro', 'author': 'K. Moses'},
        {'id': 2, 'title': 'Understanding Computers', 'author': 'B. Gibson'}
    ]
}
```