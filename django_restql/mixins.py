import copy

from rest_framework.serializers import (
    Serializer, ListSerializer,
    ValidationError
)
from django.db.models import Prefetch
from django.db.models.fields.related import(
    ManyToOneRel, ManyToManyRel
)

from .parser import Parser
from .exceptions import FieldNotFound
from .operations import ADD, CREATE, REMOVE, UPDATE
from .fields import (
    _ReplaceableField, _WritableField,
    DynamicSerializerMethodField
)


class DynamicFieldsMixin(object):
    query_param_name = "query"

    def __init__(self, *args, **kwargs):
        # Don't pass 'query', 'fields' and 'exclude' kwargs to the superclass
        self.query = kwargs.pop('query', None)  # Parsed query
        self.allowed_fields = kwargs.pop('fields', None)
        self.excluded_fields = kwargs.pop('exclude', None)
        self.return_pk = kwargs.pop('return_pk', False)

        is_field_kwarg_set = self.allowed_fields is not None
        is_exclude_kwarg_set = self.excluded_fields is not None
        msg = "May not set both `fields` and `exclude`"
        assert not(is_field_kwarg_set and is_exclude_kwarg_set), msg

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        if self.return_pk:
            return instance.pk
        return super().to_representation(instance)

    @classmethod
    def has_query_param(cls, request):
        return cls.query_param_name in request.query_params

    @classmethod
    def get_raw_query(cls, request):
        return request.query_params[cls.query_param_name]

    @classmethod
    def get_parsed_query_from_req(cls, request):
        raw_query = cls.get_raw_query(request)
        parser = Parser(raw_query)
        try:
            parsed_query = parser.get_parsed()
            return parsed_query
        except SyntaxError as e:
            msg = (
                "QueryFormatError: " + 
                e.msg + " on " + 
                e.text
            )
            raise ValidationError(msg) from None

    def get_allowed_fields(self):
        fields = super().fields
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
    def is_field_found(field_name, all_field_names, raise_error=False):
        if field_name in all_field_names:
            return True
        else:
            if raise_error:
                msg = "'%s' field is not found" % field_name
                raise ValidationError(msg)
            return False

    @staticmethod
    def is_nested_field(field_name, field, raise_error=False):
        nested_classes = (
            Serializer, ListSerializer, 
            DynamicSerializerMethodField
        )
        if isinstance(field, nested_classes):
            return True
        else:
            if raise_error:
                msg = "'%s' is not a nested field" % field_name
                raise ValidationError(msg)
            return False

    def include_fields(self):
        all_fields = self.get_allowed_fields()
        all_field_names = list(all_fields.keys())

        allowed_flat_fields = []

        # The format is  {nested_field: [sub_fields ...] ...}
        allowed_nested_fields = {}

        # The self.query["include"] contains a list of allowed fields
        # The format is [field, {nested_field: [sub_fields ...]} ...]
        included_fields =  self.query["include"]
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
                        raise_error=True
                    )
                    self.is_nested_field(
                        nested_field, 
                        all_fields[nested_field],
                        raise_error=True
                    )
                allowed_nested_fields.update(field)
            else:
                # Flat field
                self.is_field_found(field, all_field_names, raise_error=True)
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

        # The self.query["include"] contains a list of expanded nested fields
        # The format is [{nested_field: [sub_field]} ...]
        nested_fields = self.query["include"]
        for field in nested_fields:
            if field == "*":
                # Ignore this since it's not an actual field(it's just a flag)
                continue
            for nested_field in field:
                self.is_field_found(
                    nested_field,
                    all_field_names,
                    raise_error=True
                )
                self.is_nested_field(
                    nested_field,
                    all_fields[nested_field],
                    raise_error=True
                )
            allowed_nested_fields.update(field)

        # self.query["exclude"] is a list of names of excluded fields
        excluded_fields = self.query["exclude"]
        for field in excluded_fields:
            self.is_field_found(field, all_field_names, raise_error=True)
            all_fields.pop(field)

        self.nested_fields = allowed_nested_fields
        return all_fields

    @property
    def fields(self):
        request = self.context.get('request')
        
        is_not_a_request_to_process = (
            request is None or 
            request.method != "GET" or 
            not self.has_query_param(request)
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
            if self.query is None:
                # Use a query from the request
                self.query = self.get_parsed_query_from_req(request)
        elif isinstance(self.parent, ListSerializer):
            field_name = self.parent.field_name
            parent = self.parent.parent
            if hasattr(parent, "nested_fields"):
                parent_nested_fields = parent.nested_fields
                self.query = parent_nested_fields.get(field_name, None)
        elif isinstance(self.parent, Serializer):
            field_name = self.field_name
            parent = self.parent
            if hasattr(parent, "nested_fields"):
                parent_nested_fields = parent.nested_fields
                self.query = parent_nested_fields.get(field_name, None)
        else:
            # Unkown scenario
            # No filtering of fields
            return self.get_allowed_fields()

        if self.query is None:
            # No filtering on nested fields
            # Retrieve all nested fields
            return self.get_allowed_fields()

        # NOTE: self.query["include"] not being empty is not a guarantee 
        # that the exclude operator(-) has not been used because the same 
        # self.query["include"] is used to store nested fields when the
        # exclude operator(-) is used
        if self.query["exclude"]:
            # Exclude fields from a query
            return self.exclude_fields()
        elif self.query["include"]:
            # Here we are sure that self.query["exclude"] is empty
            # which means the exclude operator(-) is not used, so
            # self.query["include"] contains only fields to include
            return self.include_fields()
        else:
            # The query is empty i.e query={}
            # return nothing
            return {}


class EagerLoadingMixin(object):
    @property
    def has_query_param(self):
        if hasattr(self, "get_serializer_class"):
            serializer_class = self.get_serializer_class()

            if issubclass(serializer_class, DynamicFieldsMixin):
                return serializer_class.has_query_param(self.request)
        return False

    @property
    def parsed_query(self):
        """
        Gets parsed query for use in eager loading. 
        Defaults to the serializer parsed query assuming
        using django-restql DynamicsFieldMixin.
        """
        if self.has_query_param:
            serializer_class = self.get_serializer_class()
            return serializer_class.get_parsed_query_from_req(self.request)

        # Else include all fields
        query = {
            "include": ["*"],
            "exclude": []
        }
        return query

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
    def get_dict_parsed_query(cls, parsed_query):
        """
        Returns the parsed query as a dict.
        """
        keys = {}
        include = parsed_query.get("include", [])
        exclude = parsed_query.get("exclude", [])

        for item in include:
            if isinstance(item, str):
                keys[item] = True
            elif isinstance(item, dict):
                for key, nested_items in item.items():
                    key_base = key
                    nested_keys = cls.get_dict_parsed_query(nested_items)
                    keys[key_base] = nested_keys

        for item in exclude:
            if isinstance(item, str):
                keys[item] = False
            elif isinstance(item, dict):
                for key, nested_items in item.items():
                    key_base = key
                    nested_keys = cls.get_dict_parsed_query(nested_items)
                    keys[key_base] = nested_keys
        return keys

    @staticmethod
    def get_related_fields(related_fields_mapping, dict_parsed_query):
        """
        Returns only whitelisted related fields from a query to be used on
        `select_related` and `prefetch_related`
        """
        related_fields = []
        for key, related_field in related_fields_mapping.items():
            fields = key.split(".")
            if isinstance(related_field, str):
                related_field = [related_field]

            query_node = dict_parsed_query
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
        query = self.get_dict_parsed_query(self.parsed_query)
        select_mapping = self.get_select_related_mapping()
        prefetch_mapping = self.get_prefetch_related_mapping()

        to_select = self.get_related_fields(select_mapping, query)
        to_prefetch = self.get_related_fields(prefetch_mapping, query)

        queryset = queryset.select_related(*to_select)
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
            queryset = self.get_eager_queryset(queryset)
            return queryset
            

class NestedCreateMixin(object):
    """ Create Mixin """
    def create_writable_foreignkey_related(self, data):
        # data format {field: {sub_field: value}}
        objs = {}
        for field, value in data.items():
            # Get serializer class for nested field
            SerializerClass = type(self.get_fields()[field])
            serializer = SerializerClass(data=value, context=self.context)
            serializer.is_valid()
            obj = serializer.save()
            objs.update({field: obj})
        return objs

    def bulk_create_objs(self, field, data):
        model = self.get_fields()[field].child.Meta.model
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=self.context)
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
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    model = self.get_fields()[field].child.Meta.model
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
            for operation in values:
                if operation == ADD:
                    obj = getattr(instance, field)
                    pks = values[operation]
                    obj.set(pks)
                    field_pks.update({field: pks})
                elif operation == CREATE:
                    obj = getattr(instance, field)
                    pks = self.bulk_create_objs(field, values[operation])
                    obj.set(pks)
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
        for field in data:
            field_serializer = self.get_fields()[field]
            if isinstance(field_serializer, Serializer):
                if isinstance(field_serializer, _ReplaceableField):
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["replaceable"] \
                        .update({field: value})
                elif isinstance(field_serializer, _WritableField):
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["writable"]\
                        .update({field: value})
            elif (isinstance(field_serializer, ListSerializer) and 
                    (isinstance(field_serializer, _WritableField) or 
                    isinstance(field_serializer, _ReplaceableField))):

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


class NestedUpdateMixin(object):
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
        for field, values in data.items():
            # Get serializer class for nested field
            SerializerClass = type(self.get_fields()[field])
            nested_obj = getattr(instance, field)
            serializer = SerializerClass(
                nested_obj, 
                data=values, 
                context=self.context,
                partial=self.partial
            )
            serializer.is_valid()
            serializer.save()
            objs.update({field: nested_obj})
        return objs

    def bulk_create_many_to_many_related(self, field, nested_obj, data):
        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=self.context)
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        nested_obj.add(*pks)
        return pks

    def bulk_create_many_to_one_related(self, field, nested_obj, data):
        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=self.context)
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def bulk_update_many_to_many_related(self, field, nested_obj, data):
        # {pk: {sub_field: values}}
        objs = []

        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        for pk, values in data.items():
            obj = nested_obj.get(pk=pk)
            serializer = SerializerClass(
                obj, 
                data=values, 
                context=self.context, 
                partial=self.partial
            )
            serializer.is_valid()
            obj = serializer.save()
            objs.append(obj)
        return objs

    def bulk_update_many_to_one_related(self, field, instance, data):
        # {pk: {sub_field: values}}
        objs = []

        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        model = self.Meta.model
        foreignkey = getattr(model, field).field.name
        nested_obj = getattr(instance, field)
        for pk, values in data.items():
            obj = nested_obj.get(pk=pk)
            values.update({foreignkey: instance.pk})
            serializer = SerializerClass(
                obj, 
                data=values, 
                context=self.context, 
                partial=self.partial
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
            for operation in values:
                if operation == ADD:
                    pks = values[operation]
                    model = self.get_fields()[field].child.Meta.model
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
                        raise ValidationError(msg)
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
                        raise ValidationError(msg)
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

        # Make a partal copy of validated_data so that we can
        # iterate and alter it
        data = copy.copy(validated_data)
        for field in data:
            field_serializer = self.get_fields()[field]
            if isinstance(field_serializer, Serializer):
                if isinstance(field_serializer, _ReplaceableField):
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["replaceable"] \
                        .update({field: value})
                elif isinstance(field_serializer, _WritableField):
                    value = validated_data.pop(field)
                    fields["foreignkey_related"]["writable"] \
                        .update({field: value})
            elif (isinstance(field_serializer, ListSerializer) and
                    (isinstance(field_serializer, _WritableField) or 
                    isinstance(field_serializer, _ReplaceableField))):
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
