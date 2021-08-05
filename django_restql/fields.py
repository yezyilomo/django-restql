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
                "arguments": {},
                "aliases": {},
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

    def join_words(words, many='are', single='is'):
        word_list = ["`" + word + "`" for word in words]
        sentence = " & ".join([", ".join(word_list[:-1]), word_list[-1]])
        if len(words) > 1:
            return "%s %s" % (many, sentence)
        elif len(words) == 1:
            return "%s %s" % (single, word_list[0])
        return "%s %s" % (single, "[]")

    if not set(create_ops).issubset(set(CREATE_OPERATIONS)):
        msg = (
            "Invalid create operation(s) at `%s`, Supported operations " +
            join_words(CREATE_OPERATIONS)
        ) % "create_ops=%s" % create_ops
        raise InvalidOperation(msg)

    if not set(update_ops).issubset(set(UPDATE_OPERATIONS)):
        msg = (
            "Invalid update operation(s) at `%s`, Supported operations " +
            join_words(UPDATE_OPERATIONS)
        ) % "update_ops=%s" % update_ops
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

        def validate_data_list(self, data, partial=True):
            ListField().run_validation(data)
            model = self.parent.Meta.model
            rel = getattr(model, self.field_name).rel

            if isinstance(rel, ManyToOneRel):
                # ManyToOne Relation
                field_name = getattr(model, self.field_name).field.name
                parent_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=partial,
                    context=self.context
                )

                # Remove parent field(field_name) for validation purpose
                parent_serializer.child.fields.pop(field_name, None)

                # Check if a serializer is valid
                parent_serializer.is_valid(raise_exception=True)
            else:
                # ManyToMany Relation
                parent_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=partial,
                    context=self.context
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
            DictField().run_validation(data)
            pks = list(data.keys())
            self.validate_pk_list(pks)
            values = list(data.values())
            self.validate_data_list(values, partial=True)

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
                    raise ValidationError(detail, code=code) from None
                except KeyError:
                    msg = (
                        "`%s` is not a valid operation, valid operation(s) "
                        "for this request %s"
                        % (operation, join_words(create_ops))
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
                    raise ValidationError(detail, code=code) from None
                except KeyError:
                    msg = (
                        "`%s` is not a valid operation, valid operations(s) "
                        "for this request %s"
                        % (operation, join_words(update_ops))
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

            # All statements below are never reached
            parent_serializer = serializer_class(
                **self.child.validation_kwargs,
                data=data,
                many=True,
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

    # Remove all non validation related kwargs and
    # DynamicFieldsMixin kwargs from `valdation_kwargs`
    non_validation_related_kwargs = [
        'many', 'data', 'instance', 'context', 'fields',
        'exclude', 'return_pk', 'disable_dynamic_fields',
        'query', 'parsed_query'
    ]

    for kwarg in non_validation_related_kwargs:
        serializer_validation_kwargs.pop(kwarg, None)

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
