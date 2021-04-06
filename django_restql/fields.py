import copy

try:
    from django.utils.decorators import classproperty
except ImportError:
    from django.utils.functional import classproperty
from django.db.models.fields.related import ManyToOneRel

from rest_framework.fields import DictField, ListField, empty
from rest_framework.serializers import (
    ListSerializer, PrimaryKeyRelatedField,
    SerializerMethodField, ValidationError
)

from .exceptions import InvalidOperation
from .operations import ADD, CREATE, REMOVE, UPDATE

CREATE_OPERATIONS = (ADD, CREATE)
UPDATE_OPERATIONS = (ADD, CREATE, REMOVE, UPDATE)


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


class BaseRESTQLNestedField(object):
    def to_internal_value(self, data):
        raise NotImplementedError('`to_internal_value()` must be implemented.')


def BaseNestedFieldSerializerFactory(
        *args,
        partial=None,
        accept_pk=False,
        accept_pk_only=False,
        create_ops=CREATE_OPERATIONS,
        update_ops=UPDATE_OPERATIONS,
        serializer_class=None,
        **kwargs):
    many = kwargs.get("many", False)
    msg = (
        "May not set both `many=True` and `accept_pk=True`"
        "(accept_pk applies to foreign key relation only)."
    )
    assert not(many and (accept_pk or accept_pk_only)), msg

    msg = "May not set both `accept_pk=True` and `accept_pk_only=True`"
    assert not(accept_pk and accept_pk_only), msg

    if not set(create_ops).issubset(set(CREATE_OPERATIONS)):
        msg = (
            "Invalid create operation, Supported operations are " +
            ", ".join(CREATE_OPERATIONS)
        )
        raise InvalidOperation(msg)

    if not set(update_ops).issubset(set(UPDATE_OPERATIONS)):
        msg = (
            "Invalid update operation, Supported operations are " +
            ", ".join(UPDATE_OPERATIONS)
        )
        raise InvalidOperation(msg)

    class BaseNestedField(BaseRESTQLNestedField):
        # Original nested serializer
        @classproperty
        def serializer_class(cls):
            return serializer_class

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
                def contain_field(a): return a != field_name
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

        def get_operation_validation_methods(self, operations):
            all_operation_validation_methods = {
                ADD: self.validate_add_list,
                CREATE: self.validate_create_list,
                REMOVE: self.validate_remove_list,
                UPDATE: self.validate_update_list,
            }

            required_validation_methods = {
                operation: all_operation_validation_methods[operation]
                for operation in operations
            }

            return required_validation_methods

        def data_for_create(self, data):
            validation_methods = self.get_operation_validation_methods(create_ops)

            DictField().run_validation(data)
            for operation, values in data.items():
                try:
                    validation_methods[operation](values)
                except ValidationError as e:
                    detail = {operation: e.detail}
                    code = e.get_codes()
                    raise ValidationError(detail, code) from None
                except KeyError:
                    ops_list = ("`" + op + "`" for op in create_ops)
                    msg = (
                        "`%s` is not a valid operation, valid operations "
                        "for this request are %s"
                        % (operation, ', '.join(ops_list))
                    )
                    code = 'invalid_operation'
                    raise ValidationError(msg, code=code) from None
            return data

        def data_for_update(self, data):
            validation_methods = self.get_operation_validation_methods(update_ops)

            DictField().run_validation(data)
            for operation, values in data.items():
                try:
                    validation_methods[operation](values)
                except ValidationError as e:
                    detail = {operation: e.detail}
                    code = e.get_codes()
                    raise ValidationError(detail, code) from None
                except KeyError:
                    ops_list = ("`" + op + "`" for op in update_ops)
                    msg = (
                        "`%s` is not a valid operation, valid operations "
                        "for this request are %s"
                        % (operation, ', '.join(ops_list))
                    )
                    code = 'invalid_operation'
                    raise ValidationError(msg, code=code) from None
            return data

        def to_internal_value(self, data):
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

        # might be used before `to_internal_value` method is called
        # so we're creating this property to make sure it's available
        # as long as the class is created
        is_replaceable = accept_pk_only or accept_pk

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
            required = kwargs.get('required', True)
            default = kwargs.get('default', empty)

            if data == empty and self.is_partial:
                return empty

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

            if accept_pk_only:
                return self.validate_pk_based_nested(data)

            if accept_pk:
                if isinstance(data, dict):
                    self.is_replaceable = False
                    return self.validate_data_based_nested(data)
                else:
                    self.is_replaceable = True
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
    # TODO: Find all non validation related kwargs to remove(below are just few)

    # Remove non validation related kwargs from `valdation_kwargs`
    non_validation_kwargs = [
        'many', 'data', 'instance', 'context', 'fields',
        'exclude', 'return_pk', 'disable_dynamic_fields',
        'query',
    ]
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
