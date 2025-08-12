# Mutating Data
**Django RESTQL** got your back on creating and updating nested data too, it supports creating and updating nested data through two main components:

- `NestedModelSerializer` – handles the `create` and `update` logic for nested fields.

- `NestedField` – validates nested data before passing it to `create` or `update`.

## Using NestedField and NestedModelSerializer
Just like in querying data, mutating nested data with **Django RESTQL** is straightforward:

1. Inherit `NestedModelSerializer` in a serializer with nested fields.
2. Use `NestedField` to define any nested field you want to be able to mutate.

Example:

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
            "id", "price", "location", "amenities"
        ]
```

Example – Creating Data

```POST /api/property/```

Request body
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

Just to clarify what happed here:

- A new location was created and linked to the property.
- `create` operation added new amenities and linked them to the property.
- `add` operaton linked an existing amenity (id=3) to the property.

!!! note
    For `POST` with many-related fields, only `create` and `add` operations are supported.

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
        "update": {1: {"name": "Water"}},
        "remove": [3],
        "delete": [2]
    }
}
```

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
        {"id": 4, "name": "Bathtub"},
        {"id": 5, "name": "Fance"}
    ]
}
```

Here is what really happened after sending the update request

- `add` operation linked an existing amenity (id=4).

- `create` operation added a new amenity.

- `update` operation modified the amenity with id=1.

- `remove` operation unlinked amenity with id=3.

- `delete` operation unlinked amenity with id=2 and deleted it from the DB .

!!! note
    For PUT/PATCH with many-related fields, the supported operations are: `add`, `create`, `update`, `remove` and `delete`.


## Operations table for many-related fields

Operation | Supported In   | Description                                  |
----------|----------------|----------------------------------------------|
add	      |POST, PUT/PATCH | Adds existing related items by ID            |
create    |POST, PUT/PATCH | Creates new related items from provided data |
update    |PUT/PATCH       | Updates existing related items by ID         |
remove    |PUT/PATCH       | Removes related items (keeps them in DB)     |
delete    |PUT/PATCH       | Deletes related items from the DB            |


## Self-referencing nested fields
By default, **Django REST Framework (DRF)** does not allow you to directly declare self-referencing nested fields in serializers. However, Django itself supports self-referential relationships, and your models may include them.

**Django RESTQL** provides a clean way to handle this scenario without running into recursion issues.

Example:

```py
# models.py

class Student(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    study_partners = models.ManyToManyField("self", related_name="study_partners")
```

In this model, `study_partners` is a **self-referencing ManyToMany field** — it points to the same model(`Student`).

```py
# serializers.py

class StudentSerializer(NestedModelSerializer):
    # Define study_partners as a self-referencing nested field
    study_partners = NestedField(
        "self",  # References the same serializer
        many=True,
        required=False,
        exclude=["study_partners"]  # Prevent infinite recursion
    )

    class Meta:
        model = Student
        fields = ["id", "name", "age", "study_partners"]
```

Key Points:

- Passing `"self"` to `NestedField` tells **Django RESTQL** that this nested field should use the same serializer it’s declared in.

- Self-referencing relationships can be cyclic, leading to infinite nesting.
    Using `exclude=["study_partners"]` prevents the nested serializer from including `study_partners` again inside itself.


## NestedField kwargs

`NestedField` supports additional keyword arguments (kwargs) beyond those accepted by a serializer. These kwargs allows extra customizations when working with nested fields.

### accept_pk kwarg
**Default:** `False`

**Applies to:** ForeignKey relations only

When set to `True`, `accept_pk` lets you update a nested field using the **primary key (pk/id)** of an existing resource instead of sending the full nested object.
This is useful when you want to associate an existing resource with the parent resource without re-sending all its data.

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
            "id", "price", "location"
        ]
```

Now sending create request as


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

Using `accept_pk=True` doesn't limit you from sending full data to nested field, setting `accept_pk=True` means you can send both full data and pks. For instance from the above example you could still do 

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
**Default:** `False`

**Applies to:** ForeignKey relations only

`accept_pk_only=True` is used if you want to be able to update nested field by using pk/id only. If `accept_pk_only=True` is set you won't be able to send data to create a nested resource.

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
            "id", "price", "location"
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
    By default `accept_pk=False` and `accept_pk_only=False`, so all nested fields(foreign key related) accepts data only by default, if `accept_pk=True` is set, it accepts data and pk/id, and if `accept_pk_only=True` is set it accepts pk/id only. You can't set both `accept_pk=True` and `accept_pk_only=True`.


### create_ops and update_ops kwargs.
The `create_ops` and `update_ops` keyword arguments allow you to restrict certain operations when creating or updating nested data.
This helps to enforce rules on what clients are allowed to do during mutations.

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
        create_ops=["add"],   # Allow only "add" operation when creating
        update_ops=["add", "remove"]  # Allow only "add" and "remove" operations when updating
    )
    class Meta:
        model = Property
        fields = [
            "id", "price", "amenities"
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
    Since `create_ops=["add"]`, you can not use `create` operation in here!.

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
    Since `update_ops=["add", "remove"]`, you can not use `create`, `update` or `delete` operation in here!.

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


### allow_delete_all kwarg
This kwarg is used to enable and disable deleting all related objects on many related nested field at once by using `__all__` directive. The default value of `allow_delete_all` is `False`, which means deleting all related objects on many related nested fields is disabled by default so if you want to enable it you must set its value to `True`. For example 

```py
class CourseSerializer(NestedModelSerializer):
    books = NestedField(BookSerializer, many=True, allow_delete_all=True)

    class Meta:
        model = Course
        fields = ["name", "code", "books"]
```

With `allow_delete_all=True` as set above you will be able to send a request like

```PUT/PATCH /courses/3/```

Request Body
```js
{
    "books": {
        "delete":  "__all__"
    }
}
```

This will delete all books associated with a course being updated.


### delete_on_null kwarg
When dealing with nested fields, there are scenarios where the previously assigned object or resource is no longer needed after the field is cleared (i.e. set to `null`). In such cases, passing `delete_on_null=True` kwarg enables automatic deletion of the previously assigned resource when the nested field is explicitly updated to `null`.

This keyword argument applies only to `ForeignKey` or `OneToOne` relationships.
The default value for `delete_on_null` kwarg is `False`.

Below is an example showing how to use `delete_on_null` kwarg.
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
    location = NestedField(LocationSerializer, delete_on_null=True)
    class Meta:
        model = Property
        fields = [
            "id", "price", "location"
        ]
```

Assuming we have a property with this structure
```js
{
    "id": 1,
    "price": 30000,
    "location": {
        "id": 5,
        "city": "Arusha",
        "country": "Tanzania"
    }
}
```

Sending a mutation request to update this property by removing a location

```PUT/PATCH  /api/property/1/```

Request Body
```js
{
    "location": null
}
```

Response
```js
{
    "id": 1,
    "price": 30000,
    "location": null
}
```

In this case, the property’s location is updated to `null`, and the previously assigned Location instance (with id: 5) is deleted from the database.

!!! note
    `delete_on_null=True` can only be used when both `accept_pk=False` and `accept_pk_only=False`. This is because `accept_pk=True` or `accept_pk_only=True` typically implies that the nested object is not tightly coupled to the parent and may be referenced elsewhere. Automatically deleting it in such cases could lead to unintended side effects or broken references.


## Using DynamicFieldsMixin and NestedField together
You can combine `DynamicFieldsMixin` with `NestedModelSerializer` to create serializers that are both writable on nested fields and support dynamic field querying, this is a very common pattern.
Below is an example which shows how you can use `DynamicFieldsMixin` and `NestedField` together.

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
            "id", "price", "location"
        ]
```

`NestedField` acts as a wrapper around a serializer. It instantiates a modified version of the passed serializer class, forwarding all arguments(args) and keyword arguments(kwargs) to it.

Because of this, you can pass any argument accepted by the serializer to `NestedField`. For example, if the nested serializer inherits from `DynamicFieldsMixin` (like `LocationSerializer` above), you can use any of its supported kwargs such as:

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
                "id", "price", "location"
            ]
    ```
    
    The `required=False` kwarg allows you to create a property without including `location` field and the `allow_null=True` kwarg allows `location` field to be set to `null` if you haven't supplied it. For example

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
**Django RESTQL** supports data mutation independently of the HTTP request object. This is useful when you want to work with serializer data directly, without receiving it from an API request.

Both `NestedModelSerializer` and `NestedField` can function standalone without relying on a request.

Below is an example showing how you can work with data mutation without a request object.

```py
from rest_framework import serializers
from django_restql.fields import NestedField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer

from app.models import Book, Course


class BookSerializer(DynamicFieldsMixin, NestedModelSerializer):
    class Meta:
        model = Book
        fields = ["id", "title", "author"]


class CourseSerializer(DynamicFieldsMixin, NestedModelSerializer):
    books = NestedField(BookSerializer, many=True, required=False)
    class Meta:
        model = Course
        fields = ["id", "name", "code", "books"]
```

From serializers above you can create a course like

```py
data = {
    "name": "Computer Programming",
    "code": "CS50",
    "books": {
        "add": [1, 2],
        "create": [
            {"title": "Basic Data Structures", "author": "J. Davis"},
            {"title": "Advanced Data Structures", "author": "S. Mobit"}
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
        {"id": 1, "title": "Programming Intro", "author": "K. Moses"},
        {"id": 2, "title": "Understanding Computers", "author": "B. Gibson"},
        {"id": 3, "title": "Basic Data Structures", "author": "J. Davis"},
        {"id": 4, "title": "Advanced Data Structures", "author": "S. Mobit"}
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
        {"id": 1, "title": "Programming Intro", "author": "K. Moses"},
        {"id": 2, "title": "Understanding Computers", "author": "B. Gibson"}
    ]
}
```