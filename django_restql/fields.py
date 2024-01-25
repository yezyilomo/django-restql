try:
    from django.utils.decorators import classproperty
except ImportError:
    from django.utils.functional import classproperty
from django.db.models.fields.related import ManyToOneRel

from rest_framework.fields import (
    DictField, ListField, SkipField, Field, empty
)
from rest_framework.serializers import (
    ListSerializer, PrimaryKeyRelatedField,
    SerializerMethodField, ValidationError
)

from .parser import Query
from .exceptions import InvalidOperation
from .operations import ADD, CREATE, REMOVE, UPDATE

CREATE_OPERATIONS = (ADD, CREATE)
UPDATE_OPERATIONS = (ADD, CREATE, REMOVE, UPDATE)

ALL_RELATED_OBJS = '__all__'


class DynamicSerializerMethodField(SerializerMethodField):
    def to_representation(self, value):
        method = getattr(self.parent, self.method_name)
        is_parsed_query_available = (
            hasattr(self.parent, "restql_nested_parsed_queries") and
            self.field_name in self.parent.restql_nested_parsed_queries
        )

        if is_parsed_query_available:
            parsed_query = self.parent.restql_nested_parsed_queries[self.field_name]
        else:
            # Include all fields
            parsed_query = Query(
                field_name=None,
                included_fields=["*"],
                excluded_fields=[],
                aliases={},
                arguments={}
            )
        return method(value, parsed_query)


class BaseRESTQLNestedField(object):
    def to_internal_value(self, data):
        raise NotImplementedError('`to_internal_value()` must be implemented.')


def BaseNestedFieldSerializerFactory(
        *args,
        accept_pk=False,
        accept_pk_only=False,
        allow_remove_all=False,
        create_ops=CREATE_OPERATIONS,
        update_ops=UPDATE_OPERATIONS,
        serializer_class=None,
        **kwargs):
    many = kwargs.get("many", False)
    partial = kwargs.get("partial", None)

    assert not (
        many and (accept_pk or accept_pk_only)
    ), (
        "May not set both `many=True` and `accept_pk=True` "
        "or `accept_pk_only=True`"
        "(accept_pk and accept_pk_only applies to foreign key relation only)."
    )

    assert not (
        accept_pk and accept_pk_only
    ), "May not set both `accept_pk=True` and `accept_pk_only=True`"

    assert not (
        allow_remove_all and not many
    ), (
        "`allow_remove_all=True` can only be applied to many related "
        "nested fields, ensure the kwarg `many=True` is set."
    )

    def join_words(words, many='are', single='is'):
        word_list = ["`" + word + "`" for word in words]

        if len(words) > 1:
            sentence = " & ".join([", ".join(word_list[:-1]), word_list[-1]])
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

    if serializer_class == "self":
        # We have a self referencing serializer so the serializer
        # class is not available at the moment, we return None
        return None

    class BaseNestedField(BaseRESTQLNestedField):
        @classproperty
        def serializer_class(cls):
            # Return original nested serializer
            return serializer_class

        def is_partial(self, default):
            # Check if partial kwarg is passed if not return the default
            if partial is not None:
                return partial
            return default

    class BaseNestedFieldListSerializer(ListSerializer, BaseNestedField):
        def run_pk_list_validation(self, pks):
            ListField().run_validation(pks)
            queryset = self.child.Meta.model.objects.all()
            PrimaryKeyRelatedField(
                **self.child.validation_kwargs,
                queryset=queryset,
                many=True
            ).run_validation(pks)

        def run_data_list_validation(self, data, partial=None, operation=None):
            ListField().run_validation(data)
            model = self.parent.Meta.model
            rel = getattr(model, self.source).rel
            if isinstance(rel, ManyToOneRel):
                # ManyToOne Relation
                field_name = getattr(model, self.source).field.name
                child_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=partial,
                    context={**self.context, "parent_operation": operation}
                )

                # Remove parent field(field_name) for validation purpose
                child_serializer.child.fields.pop(field_name, None)

                # Check if a serializer is valid
                child_serializer.is_valid(raise_exception=True)
            else:
                # ManyToMany Relation
                child_serializer = serializer_class(
                    **self.child.validation_kwargs,
                    data=data,
                    many=True,
                    partial=partial,
                    context={**self.context, "parent_operation": operation}
                )

                # Check if a serializer is valid
                child_serializer.is_valid(raise_exception=True)

        def run_add_list_validation(self, data):
            self.run_pk_list_validation(data)

        def run_create_list_validation(self, data):
            self.run_data_list_validation(
                data,
                partial=self.is_partial(False),
                operation=CREATE
            )

        def run_remove_list_validation(self, data):
            if data == ALL_RELATED_OBJS:
                if not allow_remove_all:
                    msg = (
                        "Using `%s` value on `%s` operation is disabled"
                        % (ALL_RELATED_OBJS, REMOVE)
                    )
                    raise ValidationError(msg, code="not_allowed")
            else:
                self.run_pk_list_validation(data)

        def run_update_list_validation(self, data):
            DictField().run_validation(data)
            pks = list(data.keys())
            self.run_pk_list_validation(pks)
            values = list(data.values())
            self.run_data_list_validation(
                values,
                partial=self.is_partial(True),
                operation=UPDATE
            )

        def run_data_validation(self, data, allowed_ops):
            DictField().run_validation(data)

            operation_2_validation_method = {
                ADD: self.run_add_list_validation,
                CREATE: self.run_create_list_validation,
                REMOVE: self.run_remove_list_validation,
                UPDATE: self.run_update_list_validation,
            }

            allowed_operation_2_validation_method = {
                operation: operation_2_validation_method[operation]
                for operation in allowed_ops
            }

            for operation, values in data.items():
                try:
                    allowed_operation_2_validation_method[operation](values)
                except ValidationError as e:
                    detail = {operation: e.detail}
                    code = e.get_codes()
                    raise ValidationError(detail, code=code) from None
                except KeyError:
                    msg = (
                        "`%s` is not a valid operation, valid operations(s) "
                        "for this request %s"
                        % (operation, join_words(allowed_ops))
                    )
                    code = 'invalid_operation'
                    raise ValidationError(msg, code=code) from None

        def to_internal_value(self, data):
            if self.child.root.instance is None:
                parent_operation = self.context.get("parent_operation")
                if parent_operation == "update":
                    # Definitely an update
                    self.run_data_validation(data, update_ops)
                else:
                    self.run_data_validation(data, create_ops)
            else:
                # Definitely an update
                self.run_data_validation(data, update_ops)
            return data

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
            # This function can be removed on other supported DRF versions
            # i.e v3.7 v3.9 v3.10 etc doesn't need this function
            return self.to_internal_value(data)

        def run_pk_validation(self, pk):
            queryset = self.Meta.model.objects.all()
            validator = PrimaryKeyRelatedField(
                **self.validation_kwargs,
                queryset=queryset,
                many=False
            )
            # If valid return object instead of pk
            return validator.run_validation(pk)

        def run_data_validation(self, data):
            parent_operation = self.context.get("parent_operation")

            child_serializer = serializer_class(
                **self.validation_kwargs,
                data=data,
                partial=self.is_partial(
                    # Use the partial value passed, if it's not passed
                    # Use the one from the top level parent
                    True if parent_operation == UPDATE else False
                ),
                context=self.context
            )

            # Set parent to a child serializer
            child_serializer.parent = self.parent

            # Check if a serializer is valid
            child_serializer.is_valid(raise_exception=True)

            # return data to be passed to a nested serializer,
            # don't be tempted to return child_serializer.validated_data
            # cuz it changes representation of some values for instance
            # pks gets converted into objects
            return data

        def to_internal_value(self, data):
            required = kwargs.get('required', True)
            default = kwargs.get('default', empty)

            if data == empty:
                # Implementation under this block is made
                # according to DRF behaviour to other normal fields
                # For more details see
                # https://www.django-rest-framework.org/api-guide/fields/#required
                # https://www.django-rest-framework.org/api-guide/fields/#default
                # https://www.django-rest-framework.org/api-guide/fields/#allow_null
                if self.root.partial or not required:
                    # Skip the field because the update is partial
                    # or the field is not required(optional)
                    raise SkipField()
                elif required:
                    if default == empty:
                        raise ValidationError(
                            "This field is required.",
                            code='required'
                        )
                    else:
                        # Use the default value
                        data = default

            if accept_pk_only:
                return self.run_pk_validation(data)
            elif accept_pk:
                if isinstance(data, dict):
                    self.is_replaceable = False
                    return self.run_data_validation(data)
                else:
                    return self.run_pk_validation(data)
            return self.run_data_validation(data)

        def __repr__(self):
            return (
                "BaseNestedField(%s, many=False)" %
                (serializer_class.__name__, )
            )

    return {
        "serializer_class": BaseNestedFieldSerializer,
        "list_serializer_class": BaseNestedFieldListSerializer,
        "args": args,
        "kwargs": kwargs
    }


class TemporaryNestedField(Field, BaseRESTQLNestedField):
    """
    This is meant to be used temporarily when 'self' is
    passed as the first arg to `NestedField`
    """

    def __init__(
            self, NestedField, *args,
            field_args=None, field_kwargs=None, **kwargs):
        self.field_args = field_args
        self.field_kwargs = field_kwargs
        self.NestedField = NestedField
        super().__init__(*args, **kwargs)

    def get_actual_nested_field(self, serializer_class):
        # Replace "self" with the actual parent serializer class
        self.field_kwargs.update({
            "serializer_class": serializer_class
        })

        # Reproduce the actual field
        return self.NestedField(
            *self.field_args,
            **self.field_kwargs
        )


def NestedFieldWraper(*args, **kwargs):
    serializer_class = kwargs["serializer_class"]
    factory = BaseNestedFieldSerializerFactory(*args, **kwargs)

    if factory is None:
        # We have a self referencing serializer so we return
        # a temporary field while we are waiting for the parent
        # to be ready(when it's ready the parent itself will replace
        # this field with the actual field)
        return TemporaryNestedField(
            NestedFieldWraper,
            field_args=args,
            field_kwargs=kwargs
        )

    serializer_validation_kwargs = {**factory['kwargs']}

    # Remove all non validation related kwargs and
    # DynamicFieldsMixin kwargs from `valdation_kwargs`
    non_validation_related_kwargs = [
        'many', 'data', 'instance', 'context', 'fields',
        'exclude', 'return_pk', 'disable_dynamic_fields',
        'query', 'parsed_query', 'partial'
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
