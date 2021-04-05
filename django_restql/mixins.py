import copy

from django.db.models import Prefetch
from django.db.models.fields.related import ManyToManyRel, ManyToOneRel
from django.http import QueryDict
from django.utils.functional import cached_property

from rest_framework.fields import empty
from rest_framework.serializers import (
    ListSerializer, Serializer, ValidationError
)

from .exceptions import FieldNotFound, QueryFormatError
from .fields import (
    BaseRESTQLNestedField, DynamicSerializerMethodField
)
from .operations import ADD, CREATE, REMOVE, UPDATE
from .parser import Parser
from .settings import restql_settings


class RequestQueryParserMixin(object):
    """
    Mixin for parsing restql query from request.

    NOTE: We are using `request.GET` instead of
    `request.query_params` because this might be
    called before DRF request is created(i.e from dispatch).
    This means `request.query_params` might not be available
    when this mixin is used.
    """
    @staticmethod
    def get_restql_query_param_name():
        DEFAULT_QUERY_PARAM_NAME = 'query'
        query_param_name = getattr(
            restql_settings,
            "QUERY_PARAM_NAME",
            DEFAULT_QUERY_PARAM_NAME
        )
        return query_param_name

    @classmethod
    def has_restql_query_param(cls, request):
        query_param_name = cls.get_restql_query_param_name()
        return query_param_name in request.GET

    @classmethod
    def get_raw_restql_query(cls, request):
        query_param_name = cls.get_restql_query_param_name()
        return request.GET[query_param_name]

    @classmethod
    def get_parsed_restql_query_from_req(cls, request):
        if hasattr(request, 'parsed_restql_query'):
            # Use cached parsed restql query
            return request.parsed_restql_query
        raw_query = cls.get_raw_restql_query(request)
        parser = Parser(raw_query)
        parsed_restql_query = parser.get_parsed()

        # Save parsed restql query to the request so that
        # we won't need to parse it again if needed later
        request.parsed_restql_query = parsed_restql_query
        return parsed_restql_query


class QueryArgumentsMixin(RequestQueryParserMixin):
    """Mixin for converting query arguments into query parameters"""

    def get_parsed_restql_query(self, request):
        if self.has_restql_query_param(request):
            try:
                return self.get_parsed_restql_query_from_req(request)
            except (SyntaxError, QueryFormatError):
                # Let `DynamicFieldsMixin` handle this for a user
                # to get a helpful error message
                pass

        query = {
            "include": ["*"],
            "exclude": [],
            "arguments": {}
        }
        return query

    def build_query_params(self, parsed_query, parent=None):
        query_params = {}
        prefix = ''
        if parent is None:
            query_params.update(parsed_query['arguments'])
        else:
            prefix = parent + '__'
            for argument, value in parsed_query['arguments'].items():
                name = prefix + argument
                query_params.update({
                    name: value
                })
        for field in parsed_query['include']:
            if isinstance(field, dict):
                for sub_field, sub_parsed_query in field.items():
                    nested_query_params = self.build_query_params(
                        sub_parsed_query,
                        parent=prefix + sub_field
                    )
                    query_params.update(nested_query_params)
        return query_params

    def get_query_params(self, request):
        parsed = self.get_parsed_restql_query(request)
        query_params = self.build_query_params(parsed)
        return query_params

    def dispatch(self, request, *args, **kwargs):
        query_params = self.get_query_params(request)

        # We are using `request.GET` instead of `request.query_params`
        # because at this point DRF request is not yet created so
        # `request.query_params` is not yet available
        params = request.GET.copy()
        params.update(query_params)

        # Make QueryDict immutable after updating
        request.GET = QueryDict(params.urlencode(), mutable=False)
        return super().dispatch(request, *args, **kwargs)


class DynamicFieldsMixin(RequestQueryParserMixin):
    def __init__(self, *args, **kwargs):
        # Don't pass 'query', 'fields', 'exclude', 'return_pk'
        # and 'disable_dynamic_fields'  kwargs to the superclass
        self.parsed_restql_query = kwargs.pop('query', None)
        self.allowed_fields = kwargs.pop('fields', None)
        self.excluded_fields = kwargs.pop('exclude', None)
        self.return_pk = kwargs.pop('return_pk', False)
        self.disable_dynamic_fields = kwargs.pop('disable_dynamic_fields', False)

        is_field_kwarg_set = self.allowed_fields is not None
        is_exclude_kwarg_set = self.excluded_fields is not None
        msg = "May not set both `fields` and `exclude`"
        assert not(is_field_kwarg_set and is_exclude_kwarg_set), msg

        # flag to toggle using restql fields
        self._use_restql_fields = False

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        # Activate to use restql fields
        self._use_restql_fields = True

        if self.return_pk:
            return instance.pk
        return super().to_representation(instance)

    def get_allowed_fields(self):
        fields = self._all_fields
        if self.allowed_fields is not None:
            # Drop all fields which are not specified on the `fields` kwarg.
            allowed = set(self.allowed_fields)
            existing = set(fields)
            not_allowed = existing.symmetric_difference(allowed)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found" % field_name
                    raise FieldNotFound(msg) from None

        if self.excluded_fields is not None:
            # Drop all fields specified on the `exclude` kwarg.
            not_allowed = set(self.excluded_fields)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found" % field_name
                    raise FieldNotFound(msg) from None
        return fields

    @staticmethod
    def is_field_found(field_name, all_field_names, raise_exception=False):
        if field_name in all_field_names:
            return True
        else:
            if raise_exception:
                msg = "'%s' field is not found" % field_name
                raise ValidationError(msg)
            return False

    @staticmethod
    def is_nested_field(field_name, field, raise_exception=False):
        nested_classes = (
            Serializer, ListSerializer,
            DynamicSerializerMethodField
        )
        if isinstance(field, nested_classes):
            return True
        else:
            if raise_exception:
                msg = "'%s' is not a nested field" % field_name
                raise ValidationError(msg)
            return False

    def include_fields(self):
        all_fields = self.get_allowed_fields()
        all_field_names = list(all_fields.keys())

        allowed_flat_fields = []

        # The format is  {nested_field: [sub_fields ...] ...}
        allowed_nested_fields = {}

        # The self.parsed_restql_query["include"]
        # contains a list of allowed fields,
        # The format is [field, {nested_field: [sub_fields ...]} ...]
        included_fields = self.parsed_restql_query["include"]
        include_all_fields = False
        for field in included_fields:
            if field == "*":
                # Include all fields
                include_all_fields = True
                continue
            if isinstance(field, dict):
                # Nested field
                for nested_field in field:
                    self.is_field_found(
                        nested_field,
                        all_field_names,
                        raise_exception=True
                    )
                    self.is_nested_field(
                        nested_field,
                        all_fields[nested_field],
                        raise_exception=True
                    )
                allowed_nested_fields.update(field)
            else:
                # Flat field
                self.is_field_found(field, all_field_names, raise_exception=True)
                allowed_flat_fields.append(field)

        self.nested_fields = allowed_nested_fields

        if include_all_fields:
            # Return all fields
            return all_fields

        all_allowed_fields = (
            allowed_flat_fields +
            list(allowed_nested_fields.keys())
        )
        for field in all_field_names:
            if field not in all_allowed_fields:
                all_fields.pop(field)
        return all_fields

    def exclude_fields(self):
        all_fields = self.get_allowed_fields()
        all_field_names = list(all_fields.keys())

        # The format is  {nested_field: [sub_fields ...] ...}
        allowed_nested_fields = {}

        # The self.parsed_restql_query["include"]
        # contains a list of expanded nested fields
        # The format is [{nested_field: [sub_field]} ...]
        nested_fields = self.parsed_restql_query["include"]
        for field in nested_fields:
            if field == "*":
                # Ignore this since it's not an actual field(it's just a flag)
                continue
            for nested_field in field:
                self.is_field_found(
                    nested_field,
                    all_field_names,
                    raise_exception=True
                )
                self.is_nested_field(
                    nested_field,
                    all_fields[nested_field],
                    raise_exception=True
                )
            allowed_nested_fields.update(field)

        # self.parsed_restql_query["exclude"]
        # is a list of names of excluded fields
        excluded_fields = self.parsed_restql_query["exclude"]
        for field in excluded_fields:
            self.is_field_found(field, all_field_names, raise_exception=True)
            all_fields.pop(field)

        self.nested_fields = allowed_nested_fields
        return all_fields

    @cached_property
    def restql_fields(self):
        request = self.context.get('request')

        is_not_a_request_to_process = (
            request is None or
            self.disable_dynamic_fields or
            not self.has_restql_query_param(request)
        )

        if is_not_a_request_to_process:
            return self.get_allowed_fields()

        is_top_retrieve_request = (
            self.field_name is None and
            self.parent is None
        )
        is_top_list_request = (
            isinstance(self.parent, ListSerializer) and
            self.parent.parent is None and
            self.parent.field_name is None
        )

        if is_top_retrieve_request or is_top_list_request:
            if self.parsed_restql_query is None:
                # Use a parsed query from the request
                try:
                    self.parsed_restql_query = \
                        self.get_parsed_restql_query_from_req(request)
                except SyntaxError as e:
                    msg = "QuerySyntaxError: " + e.msg + " on " + e.text
                    raise ValidationError(msg) from None
                except QueryFormatError as e:
                    msg = "QueryFormatError: " + str(e)
                    raise ValidationError(msg) from None

        elif isinstance(self.parent, ListSerializer):
            field_name = self.parent.field_name
            parent = self.parent.parent
            if hasattr(parent, "nested_fields"):
                parent_nested_fields = parent.nested_fields
                self.parsed_restql_query = \
                    parent_nested_fields.get(field_name, None)
        elif isinstance(self.parent, Serializer):
            field_name = self.field_name
            parent = self.parent
            if hasattr(parent, "nested_fields"):
                parent_nested_fields = parent.nested_fields
                self.parsed_restql_query = \
                    parent_nested_fields.get(field_name, None)

        if self.parsed_restql_query is None:
            # No filtering on nested fields
            # Retrieve all nested fields
            return self.get_allowed_fields()

        # NOTE: self.parsed_restql_query["include"] not being empty
        # is not a guarantee that the exclude operator(-) has not been
        # used because the same self.parsed_restql_query["include"]
        # is used to store nested fields when the exclude operator(-) is used
        if self.parsed_restql_query["exclude"]:
            # Exclude fields from a query
            return self.exclude_fields()
        elif self.parsed_restql_query["include"]:
            # Here we are sure that self.parsed_restql_query["exclude"]
            # is empty which means the exclude operator(-) is not used,
            # so self.parsed_restql_query["include"] contains only fields
            # to include
            return self.include_fields()
        else:
            # The query is empty i.e query={}
            # return nothing
            return {}

    @cached_property
    def _all_fields(self):
        return super().fields

    @property
    def fields(self):
        if self._use_restql_fields:
            # Use restql fields
            return self.restql_fields
        return self._all_fields


class EagerLoadingMixin(RequestQueryParserMixin):
    @property
    def parsed_restql_query(self):
        """
        Gets parsed query for use in eager loading.
        Defaults to the serializer parsed query assuming
        using django-restql DynamicsFieldMixin.
        """
        if self.has_restql_query_param(self.request):
            try:
                return self.get_parsed_restql_query_from_req(self.request)
            except (SyntaxError, QueryFormatError):
                # Let `DynamicFieldsMixin` handle this for a user
                # to get a helpful error message
                pass

        # Else include all fields
        query = {
            "include": ["*"],
            "exclude": [],
            "arguments": {}
        }
        return query

    @property
    def should_auto_apply_eager_loading(self):
        if hasattr(self, 'auto_apply_eager_loading'):
            return self.auto_apply_eager_loading
        return getattr(
            restql_settings,
            "AUTO_APPLY_EAGER_LOADING",
            True
        )

    def get_select_related_mapping(self):
        if hasattr(self, "select_related"):
            return self.select_related
        # Else select nothing
        return {}

    def get_prefetch_related_mapping(self):
        if hasattr(self, "prefetch_related"):
            return self.prefetch_related
        # Else prefetch nothing
        return {}

    @classmethod
    def get_dict_parsed_restql_query(cls, parsed_restql_query):
        """
        Returns the parsed query as a dict.
        """
        keys = {}
        include = parsed_restql_query.get("include", [])
        exclude = parsed_restql_query.get("exclude", [])

        for item in include:
            if isinstance(item, str):
                keys[item] = True
            elif isinstance(item, dict):
                for key, nested_items in item.items():
                    key_base = key
                    nested_keys = cls.get_dict_parsed_restql_query(nested_items)
                    keys[key_base] = nested_keys

        for item in exclude:
            if isinstance(item, str):
                keys[item] = False
            elif isinstance(item, dict):
                for key, nested_items in item.items():
                    key_base = key
                    nested_keys = cls.get_dict_parsed_restql_query(nested_items)
                    keys[key_base] = nested_keys
        return keys

    @staticmethod
    def get_related_fields(related_fields_mapping, dict_parsed_restql_query):
        """
        Returns only whitelisted related fields from a query to be used on
        `select_related` and `prefetch_related`
        """
        related_fields = []
        for key, related_field in related_fields_mapping.items():
            fields = key.split(".")
            if isinstance(related_field, (str, Prefetch)):
                related_field = [related_field]

            query_node = dict_parsed_restql_query
            for field in fields:
                if isinstance(query_node, dict):
                    if field in query_node:
                        # Get a more specific query node
                        query_node = query_node[field]
                    elif "*" in query_node:
                        # All fields are included
                        continue
                    else:
                        # The field is not included in a query so
                        # don't include this field in `related_fields`
                        break
            else:
                # If the loop completed without breaking
                if isinstance(query_node, dict) or query_node:
                    related_fields.extend(related_field)
        return related_fields

    def apply_eager_loading(self, queryset):
        """
        Applies appropriate select_related and prefetch_related calls on a
        queryset
        """
        query = self.get_dict_parsed_restql_query(self.parsed_restql_query)
        select_mapping = self.get_select_related_mapping()
        prefetch_mapping = self.get_prefetch_related_mapping()

        to_select = self.get_related_fields(select_mapping, query)
        to_prefetch = self.get_related_fields(prefetch_mapping, query)

        if to_select:
            queryset = queryset.select_related(*to_select)
        if to_prefetch:
            queryset = queryset.prefetch_related(*to_prefetch)
        return queryset

    def get_eager_queryset(self, queryset):
        return self.apply_eager_loading(queryset)

    def get_queryset(self):
        """
        Override for DRF's get_queryset on the view.
        If get_queryset is not present, we don't try to run this.
        Instead, this can still be used by manually calling
        self.get_eager_queryset and passing in the queryset desired.
        """
        if hasattr(super(), "get_queryset"):
            queryset = super().get_queryset()
            if self.should_auto_apply_eager_loading:
                queryset = self.get_eager_queryset(queryset)
            return queryset


class BaseNestedMixin(object):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # The order in which these two methods are called is important
        self.build_restql_nested_fields()
        self.build_restql_source_field_map()

    def build_restql_nested_fields(self):
        # Make field_name -> field_value map for restql nested fields
        self.restql_nested_fields = {}
        for name, field in self.fields.items():
            if isinstance(field, BaseRESTQLNestedField):
                self.restql_nested_fields.update({name: field})

    def build_restql_source_field_map(self):
        # Make field_source -> field_value map for restql nested fields
        # You shoul run this after `build_restql_nested_fields`
        self.restql_source_field_map = {}
        for field in self.restql_nested_fields.values():
            # Get the actual source of the field
            self.restql_source_field_map.update({field.source: field})

    def to_internal_value(self, data):
        validated_data = super().to_internal_value(data)

        if self.partial:
            empty_fields = []
            restql_nested_fields = self.restql_source_field_map.keys()

            for field in restql_nested_fields:
                if field in validated_data and validated_data[field] == empty:
                    empty_fields.append(field)

            for field in empty_fields:
                # Ignore empty fields for partial update
                validated_data.pop(field)

        return validated_data


class NestedCreateMixin(BaseNestedMixin):
    """ Create Mixin """

    def create_writable_foreignkey_related(self, data):
        # data format {field: {sub_field: value}}
        objs = {}
        nested_fields = self.restql_source_field_map
        for field, value in data.items():
            # Get nested field serializer
            serializer = nested_fields[field]
            serializer_class = serializer.serializer_class
            kwargs = serializer.validation_kwargs
            serializer = serializer_class(
                **kwargs,
                data=value,
                context=self.context
            )
            serializer.is_valid()
            if value is None:
                objs.update({field: None})
            else:
                obj = serializer.save()
                objs.update({field: obj})
        return objs

    def bulk_create_objs(self, field, data):
        nested_fields = self.restql_source_field_map

        # Get nested field serializer
        serializer = nested_fields[field].child
        serializer_class = serializer.serializer_class
        kwargs = serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                context=self.context,
            )
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def create_many_to_one_related(self, instance, data):
        # data format {field: {
        # foreignkey_name: name,
        # data: {
        # ADD: [pks],
        # CREATE: [{sub_field: value}]
        # }}
        field_pks = {}
        for field, values in data.items():
            model = self.Meta.model
            foreignkey = getattr(model, field).field.name
            nested_fields = self.restql_source_field_map
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    model = nested_fields[field].child.Meta.model
                    qs = model.objects.filter(pk__in=pks)
                    qs.update(**{foreignkey: instance.pk})
                    field_pks.update({field: pks})
                elif operation == CREATE:
                    for v in values[operation]:
                        v.update({foreignkey: instance.pk})
                    pks = self.bulk_create_objs(field, values[operation])
                    field_pks.update({field: pks})
        return field_pks

    def create_many_to_many_related(self, instance, data):
        # data format {field: {
        # ADD: [pks],
        # CREATE: [{sub_field: value}]
        # }}
        field_pks = {}
        for field, values in data.items():
            obj = getattr(instance, field)
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    obj.add(*pks)
                    field_pks.update({field: pks})
                elif operation == CREATE:
                    pks = self.bulk_create_objs(field, values[operation])
                    obj.add(*pks)
                    field_pks.update({field: pks})
        return field_pks

    def create(self, validated_data):
        fields = {
            "foreignkey_related": {
                "replaceable": {},
                "writable": {}
            },
            "many_to": {
                "many_related": {},
                "one_related": {}
            }
        }

        # Make a partal copy of validated_data so that we can
        # iterate and alter it
        data = copy.copy(validated_data)
        nested_fields = self.restql_source_field_map
        for field in data:
            if field not in nested_fields:
                # Not a nested field
                continue
            else:
                field_serializer = nested_fields[field]

            if isinstance(field_serializer, Serializer):
                if field_serializer.is_replaceable:
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["replaceable"] \
                        .update({field: value})
                else:
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["writable"]\
                        .update({field: value})
            elif isinstance(field_serializer, ListSerializer):
                model = self.Meta.model
                rel = getattr(model, field).rel

                if isinstance(rel, ManyToOneRel):
                    value = validated_data.pop(field)
                    fields["many_to"]["one_related"].update({field: value})
                elif isinstance(rel, ManyToManyRel):
                    value = validated_data.pop(field)
                    fields["many_to"]["many_related"].update({field: value})
            else:
                pass

        foreignkey_related = {
            **fields["foreignkey_related"]["replaceable"],
            **self.create_writable_foreignkey_related(
                fields["foreignkey_related"]["writable"]
            )
        }

        instance = super().create({**validated_data, **foreignkey_related})

        self.create_many_to_many_related(
            instance,
            fields["many_to"]["many_related"]
        )

        self.create_many_to_one_related(
            instance,
            fields["many_to"]["one_related"]
        )

        return instance


class NestedUpdateMixin(BaseNestedMixin):
    """ Update Mixin """
    @staticmethod
    def constrain_error_prefix(field):
        return "Error on %s field: " % (field,)

    @staticmethod
    def update_replaceable_foreignkey_related(instance, data):
        # data format {field: obj}
        objs = {}
        for field, nested_obj in data.items():
            setattr(instance, field, nested_obj)
            instance.save()
            objs.update({field: instance})
        return objs

    def update_writable_foreignkey_related(self, instance, data):
        # data format {field: {sub_field: value}}
        objs = {}
        nested_fields = self.restql_source_field_map
        for field, values in data.items():
            # Get nested field serializer
            serializer = nested_fields[field]
            serializer_class = serializer.serializer_class
            kwargs = serializer.validation_kwargs
            nested_obj = getattr(instance, field)
            serializer = serializer_class(
                nested_obj,
                **kwargs,
                data=values,
                context=self.context
            )
            serializer.is_valid()
            if values is None:
                setattr(instance, field, None)
                objs.update({field: None})
            else:
                obj = serializer.save()
                if nested_obj is None:
                    # Patch back newly created object to instance
                    setattr(instance, field, obj)
                    objs.update({field: obj})
                else:
                    objs.update({field: nested_obj})
        return objs

    def bulk_create_many_to_many_related(self, field, nested_obj, data):
        # Get nested field serializer
        serializer = self.restql_source_field_map[field].child
        serializer_class = serializer.serializer_class
        kwargs = serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                context=self.context
            )
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        nested_obj.add(*pks)
        return pks

    def bulk_create_many_to_one_related(self, field, nested_obj, data):
        # Get nested field serializer
        serializer = self.restql_source_field_map[field].child
        serializer_class = serializer.serializer_class
        kwargs = serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                context=self.context
            )
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def bulk_update_many_to_many_related(self, field, nested_obj, data):
        # {pk: {sub_field: values}}
        objs = []

        # Get nested field serializer
        serializer = self.restql_source_field_map[field].child
        serializer_class = serializer.serializer_class
        kwargs = serializer.validation_kwargs
        for pk, values in data.items():
            obj = nested_obj.get(pk=pk)
            serializer = serializer_class(
                obj,
                **kwargs,
                data=values,
                context=self.context
            )
            serializer.is_valid()
            obj = serializer.save()
            objs.append(obj)
        return objs

    def bulk_update_many_to_one_related(self, field, instance, data):
        # {pk: {sub_field: values}}
        objs = []

        # Get nested field serializer
        serializer = self.restql_source_field_map[field].child
        serializer_class = serializer.serializer_class
        kwargs = serializer.validation_kwargs
        model = self.Meta.model
        foreignkey = getattr(model, field).field.name
        nested_obj = getattr(instance, field)
        for pk, values in data.items():
            obj = nested_obj.get(pk=pk)
            values.update({foreignkey: instance.pk})
            serializer = serializer_class(
                obj,
                **kwargs,
                data=values,
                context=self.context
            )
            serializer.is_valid()
            obj = serializer.save()
            objs.append(obj)
        return objs

    def update_many_to_one_related(self, instance, data):
        # data format {field: {
        # foreignkey_name: name:
        # data: {
        # ADD: [{sub_field: value}],
        # CREATE: [{sub_field: value}],
        # REMOVE: [pk],
        # UPDATE: {pk: {sub_field: value}}
        # }}}
        for field, values in data.items():
            nested_obj = getattr(instance, field)
            model = self.Meta.model
            foreignkey = getattr(model, field).field.name
            nested_fields = self.restql_source_field_map
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    model = nested_fields[field].child.Meta.model
                    qs = model.objects.filter(pk__in=pks)
                    qs.update(**{foreignkey: instance.pk})
                elif operation == CREATE:
                    for v in values[operation]:
                        v.update({foreignkey: instance.pk})
                    self.bulk_create_many_to_one_related(
                        field,
                        nested_obj,
                        values[operation]
                    )
                elif operation == REMOVE:
                    qs = nested_obj.all()
                    qs.filter(pk__in=values[operation]).delete()
                elif operation == UPDATE:
                    self.bulk_update_many_to_one_related(
                        field,
                        instance,
                        values[operation]
                    )
                else:
                    message = (
                        "%s is an invalid operation, " % (operation,)
                    )
                    raise ValidationError(message)
        return instance

    def update_many_to_many_related(self, instance, data):
        # data format {field: {
        # ADD: [{sub_field: value}],
        # CREATE: [{sub_field: value}],
        # REMOVE: [pk],
        # UPDATE: {pk: {sub_field: value}}
        # }}
        for field, values in data.items():
            nested_obj = getattr(instance, field)
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    try:
                        nested_obj.add(*pks)
                    except Exception as e:
                        msg = self.constrain_error_prefix(field) + str(e)
                        raise ValidationError(msg) from None
                elif operation == CREATE:
                    self.bulk_create_many_to_many_related(
                        field,
                        nested_obj,
                        values[operation]
                    )
                elif operation == REMOVE:
                    pks = values[operation]
                    try:
                        nested_obj.remove(*pks)
                    except Exception as e:
                        msg = self.constrain_error_prefix(field) + str(e)
                        raise ValidationError(msg) from None
                elif operation == UPDATE:
                    self.bulk_update_many_to_many_related(
                        field,
                        nested_obj,
                        values[operation]
                    )
                else:
                    message = (
                        "%s is an invalid operation, " % (operation,)
                    )
                    raise ValidationError(message)
        return instance

    def update(self, instance, validated_data):
        fields = {
            "foreignkey_related": {
                "replaceable": {},
                "writable": {}
            },
            "many_to": {
                "many_related": {},
                "one_related": {}
            }
        }

        # Make a shallow copy of validated_data so that we can
        # iterate and alter it
        data = copy.copy(validated_data)
        nested_fields = self.restql_source_field_map
        for field in data:
            # Not a nested field
            if field not in nested_fields:
                continue
            else:
                field_serializer = nested_fields[field]

            if isinstance(field_serializer, Serializer):
                if field_serializer.is_replaceable:
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["replaceable"] \
                        .update({field: value})
                else:
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["writable"] \
                        .update({field: value})
            elif isinstance(field_serializer, ListSerializer):
                model = self.Meta.model
                rel = getattr(model, field).rel

                if isinstance(rel, ManyToOneRel):
                    value = validated_data.pop(field)
                    fields["many_to"]["one_related"].update({field: value})
                elif isinstance(rel, ManyToManyRel):
                    value = validated_data.pop(field)
                    fields["many_to"]["many_related"].update({field: value})
            else:
                pass

        self.update_replaceable_foreignkey_related(
            instance,
            fields["foreignkey_related"]["replaceable"]
        )

        self.update_writable_foreignkey_related(
            instance,
            fields["foreignkey_related"]["writable"]
        )

        self.update_many_to_many_related(
            instance,
            fields["many_to"]["many_related"]
        )

        self.update_many_to_one_related(
            instance,
            fields["many_to"]["one_related"]
        )

        return super().update(instance, validated_data)
