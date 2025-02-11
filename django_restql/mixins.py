from django.http import QueryDict
from django.db.models import Prefetch
from django.utils.functional import cached_property
from django.core.exceptions import ObjectDoesNotExist
from django.db.models.fields.related import ManyToManyRel, ManyToOneRel

try:
    from django.contrib.contenttypes.fields import GenericRel
    from django.contrib.contenttypes.models import ContentType
except (RuntimeError, ImportError):
    GenericRel = None
    ContentType = None

from rest_framework.serializers import ListSerializer, Serializer, ValidationError

from .exceptions import FieldNotFound, QueryFormatError
from .fields import (
    ALL_RELATED_OBJS,
    BaseRESTQLNestedField,
    DynamicSerializerMethodField,
    TemporaryNestedField,
)
from .operations import ADD, CREATE, REMOVE, UPDATE
from .parser import Query, QueryParser
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

    @classmethod
    def has_restql_query_param(cls, request):
        query_param_name = restql_settings.QUERY_PARAM_NAME
        return query_param_name in request.GET

    @classmethod
    def get_parsed_restql_query_from_req(cls, request):
        if hasattr(request, "parsed_restql_query"):
            # Use cached parsed restql query
            return request.parsed_restql_query
        raw_query = request.GET[restql_settings.QUERY_PARAM_NAME]
        parser = QueryParser()
        parsed_restql_query = parser.parse(raw_query)

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

        # Else include all fields
        query = Query(
            field_name=None,
            included_fields=["*"],
            excluded_fields=[],
            aliases={},
            arguments={},
        )
        return query

    def build_query_params(self, parsed_query, parent=None):
        query_params = {}
        prefix = ""
        if parent is None:
            query_params.update(parsed_query.arguments)
        else:
            prefix = parent + "__"
            for argument, value in parsed_query.arguments.items():
                name = prefix + argument
                query_params.update({name: value})

        for field in parsed_query.included_fields:
            if isinstance(field, Query):
                nested_query_params = self.build_query_params(
                    field, parent=prefix + field.field_name
                )
                query_params.update(nested_query_params)
        return query_params

    def inject_query_params_in_req(self, request):
        parsed = self.get_parsed_restql_query(request)

        # Generate query params from query arguments
        query_params = self.build_query_params(parsed)

        # We are using `request.GET` instead of `request.query_params`
        # because at this point DRF request is not yet created so
        # `request.query_params` is not yet available
        params = request.GET.copy()
        params.update(query_params)

        # Make QueryDict immutable after updating
        request.GET = QueryDict(params.urlencode(), mutable=False)

    def dispatch(self, request, *args, **kwargs):
        self.inject_query_params_in_req(request)
        return super().dispatch(request, *args, **kwargs)


class DynamicFieldsMixin(RequestQueryParserMixin):
    def __init__(self, *args, **kwargs):
        # Don't pass DynamicFieldsMixin's kwargs to the superclass
        self.dynamic_fields_mixin_kwargs = {
            "query": kwargs.pop("query", None),
            "parsed_query": kwargs.pop("parsed_query", None),
            "fields": kwargs.pop("fields", None),
            "exclude": kwargs.pop("exclude", None),
            "return_pk": kwargs.pop("return_pk", False),
            "disable_dynamic_fields": kwargs.pop("disable_dynamic_fields", False),
        }

        msg = "May not set both `fields` and `exclude` kwargs"
        assert not (
            self.dynamic_fields_mixin_kwargs["fields"] is not None
            and self.dynamic_fields_mixin_kwargs["exclude"] is not None
        ), msg

        msg = "May not set both `query` and `parsed_query` kwargs"
        assert not (
            self.dynamic_fields_mixin_kwargs["query"] is not None
            and self.dynamic_fields_mixin_kwargs["parsed_query"] is not None
        ), msg

        # flag to toggle using restql fields
        self.is_ready_to_use_dynamic_fields = False

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        # Activate using restql fields
        self.is_ready_to_use_dynamic_fields = True

        if self.dynamic_fields_mixin_kwargs["return_pk"]:
            return instance.pk
        return super().to_representation(instance)

    @cached_property
    def allowed_fields(self):
        fields = super().fields
        if self.dynamic_fields_mixin_kwargs["fields"] is not None:
            # Drop all fields which are not specified on the `fields` kwarg.
            allowed = set(self.dynamic_fields_mixin_kwargs["fields"])
            existing = set(fields)
            not_allowed = existing.symmetric_difference(allowed)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found" % field_name
                    raise FieldNotFound(msg) from None

        if self.dynamic_fields_mixin_kwargs["exclude"] is not None:
            # Drop all fields specified on the `exclude` kwarg.
            not_allowed = set(self.dynamic_fields_mixin_kwargs["exclude"])
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
                msg = "`%s` field is not found" % field_name
                raise ValidationError(msg, code="not_found")
            return False

    @staticmethod
    def is_nested_field(field_name, field, raise_exception=False):
        nested_classes = (Serializer, ListSerializer, DynamicSerializerMethodField)
        if isinstance(field, nested_classes):
            return True
        else:
            if raise_exception:
                msg = "`%s` is not a nested field" % field_name
                raise ValidationError(msg, code="invalid")
            return False

    @staticmethod
    def is_valid_alias(alias):
        if len(alias) > restql_settings.MAX_ALIAS_LEN:
            msg = (
                "The length of `%s` alias has exceeded "
                "the limit specified, which is %s characters."
            ) % (alias, restql_settings.MAX_ALIAS_LEN)
            raise ValidationError(msg, code="invalid")

    def rename_aliased_fields(self, aliases, all_fields):
        for field, alias in aliases.items():
            self.is_field_found(field, all_fields, raise_exception=True)
            self.is_valid_alias(alias)
            all_fields[alias] = all_fields[field]
        return all_fields

    def select_fields(self, parsed_query, all_fields):
        self.rename_aliased_fields(parsed_query.aliases, all_fields)

        # The format is [field1, field2 ...]
        allowed_flat_fields = []

        # The format is  {nested_field: [sub_fields ...] ...}
        allowed_nested_fields = {}

        # The parsed_query.excluded_fields
        # is a list of names of excluded fields
        # The format is [field1, field2 ...]
        excluded_fields = parsed_query.excluded_fields

        # The parsed_query.included_fields
        # contains a list of allowed fields,
        # The format is [field, {nested_field: [sub_fields ...]} ...]
        included_fields = parsed_query.included_fields

        include_all_fields = False  # Assume the * is not set initially

        # Go through all included fields to check if
        # they are all valid and to set `nested_fields`
        # property on parent fields for future reference
        for field in included_fields:
            if field == "*":
                # Include all fields but ignore `*` since
                # it's not an actual field(it's just a flag)
                include_all_fields = True
                continue
            if isinstance(field, Query):
                # Nested field
                alias = parsed_query.aliases.get(field.field_name, field.field_name)

                self.is_field_found(field.field_name, all_fields, raise_exception=True)
                self.is_nested_field(
                    field.field_name, all_fields[field.field_name], raise_exception=True
                )
                allowed_nested_fields.update({alias: field})
            else:
                # Flat field
                alias = parsed_query.aliases.get(field, field)
                self.is_field_found(field, all_fields, raise_exception=True)
                allowed_flat_fields.append(alias)

        def get_duplicates(items):
            unique = []
            repeated = []
            for item in items:
                if item not in unique:
                    unique.append(item)
                else:
                    repeated.append(item)
            return repeated

        included_and_excluded_fields = (
            allowed_flat_fields + list(allowed_nested_fields.keys()) + excluded_fields
        )

        including_or_excluding_field_more_than_once = len(
            included_and_excluded_fields
        ) != len(set(included_and_excluded_fields))

        if including_or_excluding_field_more_than_once:
            repeated_fields = get_duplicates(included_and_excluded_fields)
            msg = (
                "QueryFormatError: You have either "
                "included/excluded a field more than once, "  # e.g {id, id}
                "used the same alias more than once, "  # e.g {x: name, x: age}
                "used a field name as an alias to another field or "  # e.g {id, id: age} Here age's not a parent
                "renamed a field and included/excluded it again, "  # e.g {ID: id, id}
                "The list of fields which led to this error is %s."
            ) % str(repeated_fields)
            raise ValidationError(msg, "invalid")

        if excluded_fields:
            # Here we are sure that parsed_query.excluded_fields
            # is not empty which means the user specified fields to exclude,
            # so we just check if provided fields exists then remove them from
            # a list of all fields
            for field in excluded_fields:
                self.is_field_found(field, all_fields, raise_exception=True)
                all_fields.pop(field)

        elif included_fields and not include_all_fields:
            # Here we are sure that parsed_query.excluded_fields
            # is empty which means the exclude operator(-) has not been used,
            # so parsed_query.included_fields contains only selected fields
            all_allowed_fields = set(allowed_flat_fields) | set(
                allowed_nested_fields.keys()
            )

            existing_fields = set(all_fields.keys())

            non_selected_fields = existing_fields - all_allowed_fields

            for field in non_selected_fields:
                # Remove it because we're sure it has not been selected
                all_fields.pop(field)

        elif include_all_fields:
            # Here we are sure both parsed_query.excluded_fields and
            # parsed_query.included_fields are empty, but * has been
            # used to select all fields, so we return all fields without
            # removing any
            pass

        else:
            # Otherwise the user specified empty query i.e query={}
            # So we return nothing
            all_fields = {}

        return all_fields, allowed_nested_fields

    @cached_property
    def dynamic_fields(self):
        parsed_restql_query = None

        is_root_serializer = self.parent is None or (
            isinstance(self.parent, ListSerializer) and self.parent.parent is None
        )

        if is_root_serializer:
            try:
                parsed_restql_query = self.get_parsed_restql_query()
            except SyntaxError as e:
                msg = "QuerySyntaxError: " + e.msg + " on " + e.text
                raise ValidationError(msg, code="invalid") from None
            except QueryFormatError as e:
                msg = "QueryFormatError: " + str(e)
                raise ValidationError(msg, code="invalid") from None

        elif isinstance(self.parent, ListSerializer):
            field_name = self.parent.field_name
            parent = self.parent.parent
            if hasattr(parent, "restql_nested_parsed_queries"):
                parent_nested_fields = parent.restql_nested_parsed_queries
                parsed_restql_query = parent_nested_fields.get(field_name, None)
        elif isinstance(self.parent, Serializer):
            field_name = self.field_name
            parent = self.parent
            if hasattr(parent, "restql_nested_parsed_queries"):
                parent_nested_fields = parent.restql_nested_parsed_queries
                parsed_restql_query = parent_nested_fields.get(field_name, None)

        if parsed_restql_query is None:
            # There's no query so we return all fields
            return self.allowed_fields

        # Get fields selected by `query` parameter
        selected_fields, nested_parsed_queries = self.select_fields(
            parsed_query=parsed_restql_query, all_fields=self.allowed_fields
        )

        # Keep track of parsed queries of nested fields
        # for future reference from child/nested serializers
        self.restql_nested_parsed_queries = nested_parsed_queries
        return selected_fields

    def get_parsed_restql_query_from_query_kwarg(self):
        parser = QueryParser()
        return parser.parse(self.dynamic_fields_mixin_kwargs["query"])

    def get_parsed_restql_query(self):
        request = self.context.get("request")

        if self.dynamic_fields_mixin_kwargs["query"] is not None:
            # Get from query kwarg
            return self.get_parsed_restql_query_from_query_kwarg()
        elif self.dynamic_fields_mixin_kwargs["parsed_query"] is not None:
            # Get from parsed_query kwarg
            return self.dynamic_fields_mixin_kwargs["parsed_query"]
        elif request is not None and self.has_restql_query_param(request):
            # Get from request query parameter
            return self.get_parsed_restql_query_from_req(request)
        return None  # There is no query so we return None as a parsed query

    @property
    def fields(self):
        should_use_dynamic_fields = (
            self.is_ready_to_use_dynamic_fields
            and not self.dynamic_fields_mixin_kwargs["disable_dynamic_fields"]
        )

        if should_use_dynamic_fields:
            # Return restql fields
            return self.dynamic_fields
        return self.allowed_fields


class EagerLoadingMixin(RequestQueryParserMixin):
    @property
    def parsed_restql_query(self):
        """
        Gets parsed query for use in eager loading.
        Defaults to the serializer parsed query.
        """
        if self.has_restql_query_param(self.request):
            try:
                return self.get_parsed_restql_query_from_req(self.request)
            except (SyntaxError, QueryFormatError):
                # Let `DynamicFieldsMixin` handle this for a user
                # to get a helpful error message
                pass

        # Else include all fields
        query = Query(
            field_name=None,
            included_fields=["*"],
            excluded_fields=[],
            aliases={},
            arguments={},
        )
        return query

    @property
    def should_auto_apply_eager_loading(self):
        if hasattr(self, "auto_apply_eager_loading"):
            return self.auto_apply_eager_loading
        return restql_settings.AUTO_APPLY_EAGER_LOADING

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
        parsed_query = {}
        included_fields = parsed_restql_query.included_fields
        excluded_fields = parsed_restql_query.excluded_fields

        for field in included_fields:
            if isinstance(field, Query):
                nested_keys = cls.get_dict_parsed_restql_query(field)
                parsed_query[field.field_name] = nested_keys
            else:
                parsed_query[field] = True
        for field in excluded_fields:
            if isinstance(field, Query):
                nested_keys = cls.get_dict_parsed_restql_query(field)
                parsed_query[field.field_name] = nested_keys
            else:
                parsed_query[field] = False
        return parsed_query

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
    def get_fields(self):
        # Replace all temporary fields with the actual fields
        fields = super().get_fields()
        for field_name, field in fields.items():
            if isinstance(field, TemporaryNestedField):
                fields.update(
                    {field_name: field.get_actual_nested_field(self.__class__)}
                )
        return fields

    @cached_property
    def restql_writable_nested_fields(self):
        # Make field_source -> field_value map for restql nested fields
        writable_nested_fields = {}
        for _, field in self.fields.items():
            # Get the actual source of the field
            if isinstance(field, BaseRESTQLNestedField):
                writable_nested_fields.update({field.source: field})
        return writable_nested_fields


class NestedCreateMixin(BaseNestedMixin):
    """Create Mixin"""

    def create_writable_foreignkey_related(self, data):
        # data format
        # {field: {sub_field: value}}
        objs = {}
        nested_fields = self.restql_writable_nested_fields
        for field, value in data.items():
            # Get nested field serializer
            nested_field_serializer = nested_fields[field]
            serializer_class = nested_field_serializer.serializer_class
            kwargs = nested_field_serializer.validation_kwargs
            serializer = serializer_class(
                **kwargs,
                data=value,
                # Reject partial update by default(if partial kwarg is not passed)
                # since we need all required fields when creating object
                partial=nested_field_serializer.is_partial(False),
                context={**self.context, "parent_operation": CREATE},
            )
            serializer.is_valid(raise_exception=True)
            if value is None:
                objs.update({field: None})
            else:
                obj = serializer.save()
                objs.update({field: obj})
        return objs

    def bulk_create_objs(self, field, data):
        nested_fields = self.restql_writable_nested_fields

        # Get nested field serializer
        nested_field_serializer = nested_fields[field].child
        serializer_class = nested_field_serializer.serializer_class
        kwargs = nested_field_serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                # Reject partial update by default(if partial kwarg is not passed)
                # since we need all required fields when creating object
                partial=nested_field_serializer.is_partial(False),
                context={**self.context, "parent_operation": CREATE},
            )
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def create_many_to_one_related(self, instance, data):
        # data format
        # {field: {
        # ADD: [pks],
        # CREATE: [{sub_field: value}]
        # }...}
        field_pks = {}
        for field, values in data.items():
            model = self.Meta.model
            foreignkey = getattr(model, field).field.name
            nested_fields = self.restql_writable_nested_fields
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

    def create_many_to_one_generic_related(self, instance, data):
        field_pks = {}
        nested_fields = self.restql_writable_nested_fields

        content_type = (
            ContentType.objects.get_for_model(instance) if ContentType else None
        )
        for field, values in data.items():
            relation = getattr(self.Meta.model, field).field

            nested_field_serializer = nested_fields[field].child
            serializer_class = nested_field_serializer.serializer_class
            kwargs = nested_field_serializer.validation_kwargs
            model = nested_field_serializer.Meta.model

            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    qs = model.objects.filter(pk__in=pks)
                    qs.update(
                        **{
                            relation.object_id_field_name: instance.pk,
                            relation.content_type_field_name: content_type,
                        }
                    )
                elif operation == CREATE:
                    serializer = serializer_class(
                        data=values[operation], **kwargs, many=True
                    )
                    serializer.is_valid(raise_exception=True)
                    items = serializer.validated_data

                    objs = [
                        model(
                            **item,
                            **{
                                relation.content_type_field_name: content_type,
                                relation.object_id_field_name: instance.pk,
                            },
                        )
                        for item in items
                    ]
                    objs = model.objects.bulk_create(objs)
                    field_pks[field] = [obj.pk for obj in objs]

        return field_pks

    def create_many_to_many_related(self, instance, data):
        # data format
        # {field: {
        # ADD: [pks],
        # CREATE: [{sub_field: value}]
        # }...}
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
        # Make a copy of validated_data so that we don't
        # alter it in case user need to access it later
        validated_data_copy = {**validated_data}

        fields = {
            "foreignkey_related": {"replaceable": {}, "writable": {}},
            "many_to": {
                "many_related": {},
                "one_related": {},
                "one_generic_related": {},
            },
        }

        restql_nested_fields = self.restql_writable_nested_fields
        for field in restql_nested_fields:
            if field not in validated_data_copy:
                # Nested field value is not provided
                continue

            field_serializer = restql_nested_fields[field]

            if isinstance(field_serializer, Serializer):
                if field_serializer.is_replaceable:
                    value = validated_data_copy.pop(field)
                    fields["foreignkey_related"]["replaceable"].update({field: value})
                else:
                    value = validated_data_copy.pop(field)
                    fields["foreignkey_related"]["writable"].update({field: value})
            elif isinstance(field_serializer, ListSerializer):
                model = self.Meta.model
                rel = getattr(model, field).rel

                if isinstance(rel, ManyToOneRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["one_related"].update({field: value})
                elif isinstance(rel, ManyToManyRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["many_related"].update({field: value})
                elif GenericRel and isinstance(rel, GenericRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["one_generic_related"].update({field: value})

        foreignkey_related = {
            **fields["foreignkey_related"]["replaceable"],
            **self.create_writable_foreignkey_related(
                fields["foreignkey_related"]["writable"]
            ),
        }

        instance = super().create({**validated_data_copy, **foreignkey_related})

        self.create_many_to_many_related(instance, fields["many_to"]["many_related"])

        self.create_many_to_one_related(instance, fields["many_to"]["one_related"])

        if fields["many_to"]["one_generic_related"]:
            # Call create_many_to_one_generic_related only if we have generic relationship
            self.create_many_to_one_generic_related(
                instance, fields["many_to"]["one_generic_related"]
            )

        return instance


class NestedUpdateMixin(BaseNestedMixin):
    """Update Mixin"""

    @staticmethod
    def constrain_error_prefix(field):
        return "Error on `%s` field: " % (field,)

    @staticmethod
    def update_replaceable_foreignkey_related(instance, data):
        # data format {field: obj}
        for field, nested_obj in data.items():
            setattr(instance, field, nested_obj)
        if data:
            instance.save()

    def update_writable_foreignkey_related(self, instance, data):
        # data format {field: {sub_field: value}}
        nested_fields = self.restql_writable_nested_fields

        needs_save = False
        for field, values in data.items():
            # Get nested field serializer
            nested_field_serializer = nested_fields[field]
            serializer_class = nested_field_serializer.serializer_class
            kwargs = nested_field_serializer.validation_kwargs
            nested_obj = getattr(instance, field)
            serializer = serializer_class(
                nested_obj,
                **kwargs,
                data=values,
                # Allow partial update by default(if partial kwarg is not passed)
                # since this is nested update
                partial=nested_field_serializer.is_partial(True),
                context={**self.context, "parent_operation": UPDATE},
            )
            serializer.is_valid(raise_exception=True)
            if values is None:
                setattr(instance, field, None)
                needs_save = True
            else:
                obj = serializer.save()
                if nested_obj is None:
                    # Patch back newly created object to instance
                    setattr(instance, field, obj)
                    needs_save = True
        if needs_save:
            instance.save()

    def bulk_create_many_to_many_related(self, field, nested_obj, data):
        # Get nested field serializer
        nested_field_serializer = self.restql_writable_nested_fields[field].child
        serializer_class = nested_field_serializer.serializer_class
        kwargs = nested_field_serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                # Reject partial update by default(if partial kwarg is not passed)
                # since we need all required fields when creating object
                partial=nested_field_serializer.is_partial(False),
                context={**self.context, "parent_operation": CREATE},
            )
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            pks.append(obj.pk)
        nested_obj.add(*pks)
        return pks

    def bulk_create_many_to_one_related(self, field, nested_obj, data):
        # Get nested field serializer
        nested_field_serializer = self.restql_writable_nested_fields[field].child
        serializer_class = nested_field_serializer.serializer_class
        kwargs = nested_field_serializer.validation_kwargs
        pks = []
        for values in data:
            serializer = serializer_class(
                **kwargs,
                data=values,
                # Reject partial update by default(if partial kwarg is not passed)
                # since we need all required fields when creating object
                partial=nested_field_serializer.is_partial(False),
                context={**self.context, "parent_operation": CREATE},
            )
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def bulk_update_many_to_many_related(self, field, nested_obj, data):
        # {pk: {sub_field: values}}

        # Get nested field serializer
        nested_field_serializer = self.restql_writable_nested_fields[field].child
        serializer_class = nested_field_serializer.serializer_class
        kwargs = nested_field_serializer.validation_kwargs
        for pk, values in data.items():
            try:
                obj = nested_obj.get(pk=pk)
            except ObjectDoesNotExist:
                # This pk does't belong to nested field
                continue
            serializer = serializer_class(
                obj,
                **kwargs,
                data=values,
                # Allow partial update by default(if partial kwarg is not passed)
                # since this is nested update
                partial=nested_field_serializer.is_partial(True),
                context={**self.context, "parent_operation": UPDATE},
            )
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()

    def bulk_update_many_to_one_related(
        self, field, instance, data, update_foreign_key=True
    ):
        # {pk: {sub_field: values}}

        # Get nested field serializer
        nested_field_serializer = self.restql_writable_nested_fields[field].child
        serializer_class = nested_field_serializer.serializer_class
        kwargs = nested_field_serializer.validation_kwargs
        model = self.Meta.model
        foreignkey = getattr(model, field).field.name
        nested_obj = getattr(instance, field)
        for pk, values in data.items():
            try:
                obj = nested_obj.get(pk=pk)
            except ObjectDoesNotExist:
                # This pk does't belong to nested field
                continue
            if update_foreign_key:
                values.update({foreignkey: instance.pk})
            serializer = serializer_class(
                obj,
                **kwargs,
                data=values,
                # Allow partial update by default(if partial kwarg is not passed)
                # since this is nested update
                partial=nested_field_serializer.is_partial(True),
                context={**self.context, "parent_operation": UPDATE},
            )
            serializer.is_valid(raise_exception=True)
            obj = serializer.save()

    def update_many_to_one_related(self, instance, data):
        # data format
        # {field: {
        # ADD: [{sub_field: value}],
        # CREATE: [{sub_field: value}],
        # REMOVE: [pk],
        # UPDATE: {pk: {sub_field: value}}
        # }...}
        for field, values in data.items():
            nested_obj = getattr(instance, field)
            model = self.Meta.model
            foreignkey = getattr(model, field).field.name
            nested_fields = self.restql_writable_nested_fields
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
                        field, nested_obj, values[operation]
                    )
                elif operation == REMOVE:
                    qs = nested_obj.all()
                    if values[operation] == ALL_RELATED_OBJS:
                        qs.delete()
                    else:
                        qs.filter(pk__in=values[operation]).delete()
                elif operation == UPDATE:
                    self.bulk_update_many_to_one_related(
                        field, instance, values[operation]
                    )
                else:
                    message = "`%s` is an invalid operation" % (operation,)
                    raise ValidationError(message, code="invalid_operation")
        return instance

    def update_many_to_one_generic_related(self, instance, data):
        # it's same logic for add & create operations
        # which are already handled by NestedCreateMixin
        NestedCreateMixin.create_many_to_one_generic_related(self, instance, data)

        for field, values in data.items():
            nested_qs = getattr(instance, field)
            for operation in values:
                if operation not in [ADD, CREATE, UPDATE, REMOVE]:
                    message = f"`{operation}` is an invalid operation"
                    raise ValidationError(message, code="invalid_operation")

                if operation == REMOVE:
                    qs = nested_qs.all()
                    if values[operation] == ALL_RELATED_OBJS:
                        qs.delete()
                    else:
                        qs.filter(pk__in=values[operation]).delete()
                elif operation == UPDATE:
                    self.bulk_update_many_to_one_related(
                        field, instance, values[operation], update_foreign_key=False
                    )
        return instance

    def update_many_to_many_related(self, instance, data):
        # data format
        # {field: {
        # ADD: [{sub_field: value}],
        # CREATE: [{sub_field: value}],
        # REMOVE: [pk],
        # UPDATE: {pk: {sub_field: value}}
        # }...}
        for field, values in data.items():
            nested_obj = getattr(instance, field)
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    try:
                        nested_obj.add(*pks)
                    except Exception as e:
                        msg = self.constrain_error_prefix(field) + str(e)
                        code = "constrain_error"
                        raise ValidationError(msg, code=code) from None
                elif operation == CREATE:
                    self.bulk_create_many_to_many_related(
                        field, nested_obj, values[operation]
                    )
                elif operation == REMOVE:
                    pks = values[operation]
                    if pks == ALL_RELATED_OBJS:
                        pks = nested_obj.all()
                    try:
                        nested_obj.remove(*pks)
                    except Exception as e:
                        msg = self.constrain_error_prefix(field) + str(e)
                        code = "constrain_error"
                        raise ValidationError(msg, code=code) from None
                elif operation == UPDATE:
                    self.bulk_update_many_to_many_related(
                        field, nested_obj, values[operation]
                    )
                else:
                    message = "`%s` is an invalid operation" % (operation,)
                    raise ValidationError(message, code="invalid_operation")
        return instance

    def update(self, instance, validated_data):
        # Make a copty of validated_data so that we don't
        # alter it in case user need to access it later
        validated_data_copy = {**validated_data}

        fields = {
            "foreignkey_related": {"replaceable": {}, "writable": {}},
            "many_to": {
                "many_related": {},
                "one_related": {},
                "one_generic_related": {},
            },
        }

        restql_nested_fields = self.restql_writable_nested_fields
        for field in restql_nested_fields:
            if field not in validated_data_copy:
                # Nested field value is not provided
                continue

            field_serializer = restql_nested_fields[field]

            if isinstance(field_serializer, Serializer):
                if field_serializer.is_replaceable:
                    value = validated_data_copy.pop(field)
                    fields["foreignkey_related"]["replaceable"].update({field: value})
                else:
                    value = validated_data_copy.pop(field)
                    fields["foreignkey_related"]["writable"].update({field: value})
            elif isinstance(field_serializer, ListSerializer):
                model = self.Meta.model
                rel = getattr(model, field).rel

                if isinstance(rel, ManyToOneRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["one_related"].update({field: value})
                elif isinstance(rel, ManyToManyRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["many_related"].update({field: value})
                elif GenericRel and isinstance(rel, GenericRel):
                    value = validated_data_copy.pop(field)
                    fields["many_to"]["one_generic_related"].update({field: value})

        instance = super().update(instance, validated_data_copy)

        self.update_replaceable_foreignkey_related(
            instance, fields["foreignkey_related"]["replaceable"]
        )

        self.update_writable_foreignkey_related(
            instance, fields["foreignkey_related"]["writable"]
        )

        self.update_many_to_many_related(instance, fields["many_to"]["many_related"])

        self.update_many_to_one_related(instance, fields["many_to"]["one_related"])

        if fields["many_to"]["one_generic_related"]:
            # Call update_many_to_one_generic_related only if we have generic relationship
            self.update_many_to_one_generic_related(
                instance, fields["many_to"]["one_generic_related"]
            )
        return instance
