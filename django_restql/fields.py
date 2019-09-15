import copy

from rest_framework.serializers import (
    Serializer, ListSerializer, 
    ValidationError, PrimaryKeyRelatedField
)
from django.db.models.fields.related import ManyToOneRel

from .exceptions import InvalidOperation
from .operations import ADD, CREATE, REMOVE, UPDATE


CREATE_SUPPORTED_OPERATIONS = (ADD, CREATE)
UPDATE_SUPPORTED_OPERATIONS = (ADD, CREATE, REMOVE, UPDATE)

class _ReplaceableField(object):
    pass

class _WritableField(object):
    pass

def BaseNestedFieldSerializerFactory(*args, 
                                     accept_pk=False, 
                                     create_ops=[ADD, CREATE], 
                                     update_ops=[ADD, CREATE, REMOVE, UPDATE], 
                                     serializer_class=None, 
                                     **kwargs):
    BaseClass = _ReplaceableField if accept_pk else _WritableField
    
    if not set(create_ops).issubset(set(CREATE_SUPPORTED_OPERATIONS)):
        msg = (
            "Invalid create operation, Supported operations are " +
            ", ".join(CREATE_SUPPORTED_OPERATIONS)
        )
        raise InvalidOperation(msg)

    if not set(update_ops).issubset(set(UPDATE_SUPPORTED_OPERATIONS)):
        msg = (
            "Invalid update operation, Supported operations are " +
            ", ".join(UPDATE_SUPPORTED_OPERATIONS)
        )
        raise InvalidOperation(msg)

    class BaseNestedFieldListSerializer(ListSerializer, BaseClass):
        @property
        def is_partial(self):
            request = self.context.get('request')
            partial = True if request.method == "PATCH" else False
            return partial

        def validate_pk_list(self, pks):
            queryset = self.child.Meta.model.objects.all()
            validator = PrimaryKeyRelatedField(
                queryset=queryset, 
                many=True 
            )
            return validator.run_validation(pks)
    
        def validate_data_list(self, data, partial=False):
            request = self.context.get('request')
            context = {"request": request}
            model = self.parent.Meta.model
            rel = getattr(model, self.source).rel

            if isinstance(rel, ManyToOneRel):
                # ManyToOne Relation
                field_name = getattr(model, self.source).field.name
                # remove field_name to validated fields
                contain_field = lambda a: a != field_name
                fields = filter(contain_field, serializer_class.Meta.fields)
                original_fields = copy.copy(serializer_class.Meta.fields)
                serializer_class.Meta.fields = list(fields)
                parent_serializer = serializer_class(
                    data=data, 
                    many=True, 
                    partial=partial,
                    context=context
                )
                parent_serializer.is_valid(raise_exception=True)
                serializer_class.Meta.fields = original_fields
            else:
                # ManyToMany Relation
                parent_serializer = serializer_class(
                    data=data, 
                    many=True, 
                    partial=partial,
                    context={"request": request}
                )
                parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data
    
        def validate_add_list(self, data):
            return self.validate_pk_list(data)

        def validate_create_list(self, data):
            return self.validate_data_list(data, partial=False)
    
        def validate_remove_list(self, data):
            return self.validate_pk_list(data)
    
        def validate_update_list(self, data):
            # Obtain pks & data then
            if isinstance(data, dict):
                self.validate_pk_list(data.keys())
                values = list(data.values())
                self.validate_data_list(values, partial=self.is_partial)
            else:
                raise ValidationError(
                    "Expected data of form {'pk': 'data'..}"
                )

        def create_data_is_valid(self, data):
            if (isinstance(data, dict) and 
                    set(data.keys()).issubset(create_ops)):
                return True
            return False

        def data_for_create(self, data):
            validate = {
                ADD: self.validate_add_list,
                CREATE: self.validate_create_list, 
            }

            if self.create_data_is_valid(data):
                for operation, values in data.items():
                    validate[operation](values)
                return data
            else:
                wrap_quotes = lambda op: "'" + op + "'"
                op_list =list(map(wrap_quotes, create_ops))
                msg = (
                    "Expected data of form " +
                    "{" + ": [..], ".join(op_list) + ": [..]}"
                )
                raise ValidationError(msg)

        def update_data_is_valid(self, data):
            if (isinstance(data, dict) and 
                    set(data.keys()).issubset(update_ops)):
                return True
            return False

        def data_for_update(self, data):
            validate = {
                ADD: self.validate_add_list,
                CREATE: self.validate_create_list, 
                REMOVE: self.validate_remove_list, 
                UPDATE: self.validate_update_list,
            }

            if self.update_data_is_valid(data):
                for operation, values in data.items():
                    validate[operation](values)
                return data
            else:
                wrap_quotes = lambda op: "'" + op + "'"
                op_list =list(map(wrap_quotes, update_ops))
                msg = (
                    "Expected data of form " +
                    "{" + ": [..], ".join(op_list) + ": [..]}"
                )
                raise ValidationError(msg)

        def to_internal_value(self, data):
            request = self.context.get('request')
            context={"request": request}
            if  request.method in ["PUT", "PATCH"]:
                return self.data_for_update(data)

            if request.method in ["POST"]:
                return self.data_for_create(data)

            parent_serializer = serializer_class(
                data=data, 
                many=True, 
                partial=self.is_partial,
                context=context
            )
            parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data

        def __repr__(self):
            return (
                "BaseNestedField(%s, many=True)" % 
                (serializer_class.__name__, )
            )

    class BaseNestedFieldSerializer(serializer_class, BaseClass):
        class Meta(serializer_class.Meta):
            list_serializer_class = BaseNestedFieldListSerializer

        @property
        def is_partial(self):
            request = self.context.get('request')
            partial = True if request.method == "PATCH" else False
            return partial

        def run_validation(self, data):
            # Run `to_internal_value` only nothing more
            # This is needed only on DRF 3.8.x due to a bug on it
            # This function can be removed on other supported DRF verions 
            # i.e v3.7 v3.9 v3.10 doesn't need this function
            return self.to_internal_value(data)

        def validate_pk_based_nested(self, data):
            queryset = self.Meta.model.objects.all()
            validator = PrimaryKeyRelatedField(
                queryset=queryset,
                many=False
            )
            obj = validator.run_validation(data)
            return obj

        def validate_data_based_nested(self, data):
            request = self.context.get("request")
            context={"request": request}
            parent_serializer = serializer_class(
                data=data, 
                partial=self.is_partial,
                context=context
            )
            parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data

        def to_internal_value(self, data):
            if accept_pk:
                return self.validate_pk_based_nested(data)
            return self.validate_data_based_nested(data)

        def __repr__(self):
            return (
                "BaseNestedField(%s, many=False)" % 
                (serializer_class.__name__, )
            )

    kwargs.update({"read_only": False, "write_only": False})
    return {
        "serializer_class": BaseNestedFieldSerializer,
        "list_serializer_class": BaseNestedFieldListSerializer,
        "args": args,
        "kwargs": kwargs
    }



def NestedFieldWraper(*args, **kwargs):
    factory = BaseNestedFieldSerializerFactory(*args, **kwargs)
    serializer_class = kwargs["serializer_class"]

    class NestedListSerializer(factory["list_serializer_class"]):
        def __repr__(self):
            return (
                "NestedField(%s, many=False)" % 
                (serializer_class.__name__, )
            )

    class NestedSerializer(factory["serializer_class"]):
        class Meta(factory["serializer_class"].Meta):
            list_serializer_class = NestedListSerializer

        def __repr__(self):
            return (
                "NestedField(%s, many=False)" % 
                (serializer_class.__name__, )
            )
  
    return NestedSerializer(
        *factory["args"],
        **factory["kwargs"]
    )


def NestedField(serializer_class, *args, **kwargs):
    return NestedFieldWraper(
        *args, 
        serializer_class=serializer_class, 
        **kwargs
    )

