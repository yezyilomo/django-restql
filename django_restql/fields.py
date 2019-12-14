import copy

from rest_framework.fields import (
    empty, ListField, DictField
)
from rest_framework.serializers import (
    Serializer, ListSerializer, SerializerMethodField,
    ValidationError, PrimaryKeyRelatedField
)
from django.db.models.fields.related import ManyToOneRel

from .exceptions import InvalidOperation
from .operations import ADD, CREATE, REMOVE, UPDATE


CREATE_SUPPORTED_OPERATIONS = (ADD, CREATE)
UPDATE_SUPPORTED_OPERATIONS = (ADD, CREATE, REMOVE, UPDATE)


class DynamicSerializerMethodField(SerializerMethodField):
    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        if (hasattr(self.parent, "nested_fields") and 
                self.field_name in self.parent.nested_fields):
            query = self.parent.nested_fields[self.field_name]
        else:
            # Include all fields
            query = {
                "include": ["*"],
                "exclude": [],
                "arguments": {}
            }
        return method(value, query)


class BaseReplaceableNestedField(object):
    def to_internal_value(self, data):
        raise NotImplementedError('`to_internal_value()` must be implemented.')


class BaseWritableNestedField(object):
    def to_internal_value(self, data):
        raise NotImplementedError('`to_internal_value()` must be implemented.')


def BaseNestedFieldSerializerFactory(
        *args,
        partial=None,
        accept_pk=False,
        create_ops=[ADD, CREATE],
        update_ops=[ADD, CREATE, REMOVE, UPDATE],
        serializer_class=None,
        **kwargs):
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
    
    BaseClass = BaseReplaceableNestedField if accept_pk \
        else BaseWritableNestedField

    class BaseNestedField(BaseClass):
        @property
        def is_partial(self):
            if partial is None and self.parent is not None:
                return self.parent.partial
            else:
                return partial

    class BaseNestedFieldListSerializer(ListSerializer, BaseNestedField):

        def validate_pk_list(self, pks):
            ListField().run_validation(pks)
            queryset = self.child.Meta.model.objects.all()
            validator = PrimaryKeyRelatedField(
                queryset=queryset,
                many=True
            )
            return validator.run_validation(pks)
    
        def validate_data_list(self, data):
            ListField().run_validation(data)
            model = self.parent.Meta.model
            rel = getattr(model, self.field_name).rel

            if isinstance(rel, ManyToOneRel):
                # ManyToOne Relation
                field_name = getattr(model, self.field_name).field.name
                # remove field_name to validated fields
                contain_field = lambda a: a != field_name
                fields = filter(contain_field, serializer_class.Meta.fields)
                original_fields = copy.copy(serializer_class.Meta.fields)
                serializer_class.Meta.fields = list(fields)
                parent_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=self.is_partial,
                    context=self.context
                )
                parent_serializer.is_valid(raise_exception=True)
                serializer_class.Meta.fields = original_fields
            else:
                # ManyToMany Relation
                parent_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=self.is_partial,
                    context=self.context
                )
                parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data
    
        def validate_add_list(self, data):
            return self.validate_pk_list(data)

        def validate_create_list(self, data):
            return self.validate_data_list(data)
    
        def validate_remove_list(self, data):
            return self.validate_pk_list(data)
    
        def validate_update_list(self, data):
            DictField().run_validation(data)
            pks = list(data.keys())
            self.validate_pk_list(pks)
            values = list(data.values())
            self.validate_data_list(values)

        def data_for_create(self, data):
            validate = {
                ADD: self.validate_add_list,
                CREATE: self.validate_create_list,
            }

            DictField().run_validation(data)
            for operation, values in data.items():
                try:
                    validate[operation](values)
                except ValidationError as e:
                    detail = {operation: e.detail}
                    code = e.get_codes()
                    raise ValidationError(detail, code) from None
                except KeyError:
                    wrap_quotes = lambda op: "`" + op + "`"
                    op_list =list(map(wrap_quotes, create_ops))
                    msg = (
                        "`%s` is not a valid operation, valid operations "
                        "for this request are %s" 
                        % (operation, ', '.join(op_list))
                    )
                    code = 'invalid_operation'
                    raise ValidationError(msg, code=code) from None
            return data

        def data_for_update(self, data):
            validate = {
                ADD: self.validate_add_list,
                CREATE: self.validate_create_list,
                REMOVE: self.validate_remove_list,
                UPDATE: self.validate_update_list,
            }

            DictField().run_validation(data)
            for operation, values in data.items():
                try:
                    validate[operation](values)
                except ValidationError as e:
                    detail = {operation: e.detail}
                    code = e.get_codes()
                    raise ValidationError(detail, code) from None
                except KeyError:
                    wrap_quotes = lambda op: "`" + op + "`"
                    op_list =list(map(wrap_quotes, update_ops))
                    msg = (
                        "`%s` is not a valid operation, valid operations "
                        "for this request are %s" 
                        % (operation, ', '.join(op_list))
                    )
                    code='invalid_operation'
                    raise ValidationError(msg, code=code) from None
            return data

        def to_internal_value(self, data):
            source = kwargs.get('source', None)
            if source is not None and self.parent is not None:
                alias = self.field_name
                self.parent._aliased_nested_fields.update({source: self})
                self.parent._unaliased_fields.pop(alias)
            required = kwargs.get('required', True)
            request = self.context.get('request')
            if request.method in ["PUT", "PATCH"]:
                return self.data_for_update(data)

            if request.method in ["POST"]:
                return self.data_for_create(data)

            parent_serializer = serializer_class(
                **self.child.validation_kwargs,
                data=data,
                many=True,
                partial=self.is_partial,
                context=self.context
            )
            parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data

        def __repr__(self):
            return (
                "BaseNestedField(%s, many=True)" % 
                (serializer_class.__name__, )
            )

    class BaseNestedFieldSerializer(serializer_class, BaseNestedField):
        class Meta(serializer_class.Meta):
            list_serializer_class = BaseNestedFieldListSerializer

        def run_validation(self, data):
            # Run `to_internal_value` only nothing more
            # This is needed only on DRF 3.8.x due to a bug on it
            # This function can be removed on other supported DRF verions 
            # i.e v3.7 v3.9 v3.10 doesn't need this function
            return self.to_internal_value(data)

        def validate_pk_based_nested(self, data):
            queryset = self.Meta.model.objects.all()
            validator = PrimaryKeyRelatedField(
                **self.validation_kwargs,
                queryset=queryset,
                many=False
            )
            obj = validator.run_validation(data)
            return obj

        def validate_data_based_nested(self, data):
            parent_serializer = serializer_class(
                **self.validation_kwargs,
                data=data,
                partial=self.is_partial,
                context=self.context
            )
            parent_serializer.is_valid(raise_exception=True)
            return parent_serializer.validated_data

        def to_internal_value(self, data):
            source = kwargs.get('source', None)
            if source is not None and self.parent is not None:
                alias = self.field_name
                self.parent._aliased_nested_fields.update({source: self})
                self.parent._unaliased_fields.pop(alias)
            required = kwargs.get('required', True)
            default = kwargs.get('default', empty)

            if data == empty and required and default == empty:
                raise ValidationError(
                    "This field is required.",
                    code='required'
                )
            elif data == empty and required:
                data = default
            elif data == empty and default == empty:
                data = ""
                
            if data == "":
                data = None
            if accept_pk:
                return self.validate_pk_based_nested(data)
            return self.validate_data_based_nested(data)

        def __repr__(self):
            return (
                "BaseNestedField(%s, many=False)" % 
                (serializer_class.__name__, )
            )

    read_only = kwargs.get('read_only', False)
    write_only = kwargs.get('write_only', False)
    kwargs.update({"read_only": read_only, "write_only": write_only})
    return {
        "serializer_class": BaseNestedFieldSerializer,
        "list_serializer_class": BaseNestedFieldListSerializer,
        "args": args,
        "kwargs": kwargs
    }


def NestedFieldWraper(*args, **kwargs):
    factory = BaseNestedFieldSerializerFactory(*args, **kwargs)
    serializer_class = kwargs["serializer_class"]

    serializer_validation_kwargs = {**factory['kwargs']}
    # TODO: Find all non validation kwargs to remove(below are just few)

    # Remove non validation related kwargs from `valdation_kwargs`
    non_validation_kwargs = ['many', 'data', 'instance', 'context']
    for kwarg in non_validation_kwargs:
        if kwarg in serializer_validation_kwargs:
            serializer_validation_kwargs.pop(kwarg)

    class NestedListSerializer(factory["list_serializer_class"]):
        def __repr__(self):
            return (
                "NestedField(%s, many=False)" % 
                (serializer_class.__name__, )
            )
            
    class NestedSerializer(factory["serializer_class"]):
        # set validation related kwargs to be used on 
        # `NestedCreateMixin` and `NestedUpdateMixin`
        validation_kwargs = serializer_validation_kwargs
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
        **kwargs,
        serializer_class=serializer_class
    )
