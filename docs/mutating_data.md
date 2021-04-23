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
What's done here is pretty clear, location will be created and associated with the property created, also create operation on amenities will create amenities with values specified in a list and associate with the property, add operation will add amenity with id 3 to a list of amenities of the property.

!!! note
    POST for many related field supports two operations which are `create` and `add`.

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

Here `add`, `create`, `remove` and `update` are operations, so `add` operation add amenitiy with id 4 to a list of amenities of the property, `create` operation create amenities with values specified in a list, `remove` operation dessociate amenities with id 3 from a property, `update` operation edit amenity with id 1 according to values specified.


!!! note
    PUT/PATCH for many related field supports four operations which are `create`, `add`, `remove` and `update`.

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
`accept_pk=True` is used if you want to be able to update nested field by using pk/id of existing data(basically associate existing nested resources with the parent resource). This applies to ForeignKey relation only.

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
!!! note
    Here location resource with id 2 is already existing, so what's done here is create new property resource and associate it with a location with id 2.

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
<br>

## Using NestedField with accept_pk_only kwarg.
`accept_pk_only=True` is used if you want to be able to update nested field by using pk/id only. This applies to ForeignKey relation only. If this is set you won't be able to send data to create a nested resource.

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
<br>


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
    By default `accept_pk=False` and `accept_pk_only=False`, so nested field(foreign key related) accepts data only by default, if `accept_pk=True` is set, it accepts data and pk/id, and if `accept_pk_only=True` is set it accepts pk/id only. You can't set both `accept_pk=True` and `accept_pk_only=True` at the same time.
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

`NestedField` is nothing but a serializer wrapper, it returns an instance of a modified version of a serializer passed, so you can pass all the args and kwargs accepted by a serializer on it, it will simply pass them to a serializer passed when instantiating an instance. So you can pass anything accepted by a serializer to a `NestedField` wrapper, and if a serializer passed inherits `DynamicFieldsMixin` just like `LocationSerializer` on above example then you can pass any arg or kwarg accepted by `DynamicFieldsMixin` when defining location as a nested field, i.e

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

The `required=False` kwarg allows you to create Property without including `location` field and the `allow_null=True` kwarg allows `location` field to be set to null if you haven't supplied it e.g

```POST /api/property/```

Request Body
```js
{
    "price": 40000
    // You can see that the location is not included here
}
```

<br>

Response
```js
{
    "id": 2,
    "price": 50000,
    "location": null  // This is the result of not including location
}
```

If you use `required=False` only without `allow_null=True`, The serializer will allow you to create Property without including `location` field but it will throw error because by default `allow_null=False` which means `null`/`None`(which is what's passed when you don't supply `location` value) is not considered a valid value.