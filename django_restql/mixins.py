import copy

from rest_framework.serializers import (
    Serializer, ListSerializer, 
    ValidationError
)
from django.db.models.fields.related import(
    ManyToOneRel, ManyToManyRel
)

from .parser import Parser
from .exceptions import FieldNotFound
from .operations import ADD, CREATE, REMOVE, UPDATE
from .fields import _ReplaceableField, _WritableField


class DynamicFieldsMixin(object):
    query_param_name = "query"

    def __init__(self, *args, **kwargs):
        # Don't pass the 'fields' and 'exclude' arg up to the superclass
        self.allowed_fields = kwargs.pop('fields', None)
        self.excluded_fields = kwargs.pop('exclude', None)
        self.return_pk = kwargs.pop('return_pk', False)

        is_field_set = self.allowed_fields is not None
        is_exclude_set = self.excluded_fields is not None
        msg = "May not set both `fields` and `exclude`"
        assert not(is_field_set and is_exclude_set), msg

        # Instantiate the superclass normally
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        if self.return_pk:
            return instance.pk
        return super().to_representation(instance)

    def has_query_param(self, request):
        return self.query_param_name in request.query_params

    def get_query_str(self, request):
        return request.query_params[self.query_param_name]

    def get_allowed_fields(self):
        fields = super().fields
        if self.allowed_fields is not None:
            # Drop any fields that are not specified on `fields` argument.
            allowed = set(self.allowed_fields)
            existing = set(fields)
            not_allowed = existing.symmetric_difference(allowed)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found"%field_name
                    raise FieldNotFound(msg) from None

        if self.excluded_fields is not None:
            # Drop any fields that are not specified on `exclude` argument.
            not_allowed = set(self.excluded_fields)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found"%field_name
                    raise FieldNotFound(msg) from None
        return fields

    @property
    def fields(self):
        fields = self.get_allowed_fields()
        request = self.context.get('request')
        
        is_not_a_request_to_process = (
            request is None or 
            request.method != "GET" or 
            not self.has_query_param(request)
        )

        if is_not_a_request_to_process:
            return fields

        is_top_retrieve_request = (
            self.field_name is None and 
            self.parent is None
        )
        is_top_list_request = (
            isinstance(self.parent, ListSerializer) and 
            self.parent.parent is None
        )

        if is_top_retrieve_request or is_top_list_request:
                query_str = self.get_query_str(request)
                parser = Parser(query_str)
                try:
                    fields_query = parser.get_parsed()
                except SyntaxError as e:
                    msg = (
                        "QueryFormatError: " + 
                        e.msg + " on " + 
                        e.text
                    )
                    raise ValidationError(msg) from None
                    
        elif isinstance(self.parent, ListSerializer):
            field_name = self.parent.field_name
            parent = self.parent.parent
            fields_query = []
            if hasattr(parent, "nested_fields_queries"):
                fields_query = parent.nested_fields_queries.get(field_name, None)
        elif isinstance(self.parent, Serializer):
            field_name = self.field_name
            parent = self.parent
            fields_query = []
            if hasattr(parent, "nested_fields_queries"):
                fields_query = parent.nested_fields_queries.get(field_name, None)
        else:
            # Unkown scenario
            return fields

        if fields_query is None:
            # No filtering on nested fields
            # Retrieve all nested fields
            return fields
            
        all_fields = list(fields.keys())
        allowed_nested_fields = {}
        allowed_flat_fields = []
        for field in fields_query:
            if isinstance(field, dict):
                # Nested field
                for nested_field in field:
                    if nested_field not in all_fields:
                        msg = "'%s' field is not found" % field
                        raise ValidationError(msg)
                    nested_classes = (Serializer, ListSerializer)
                    if not isinstance(fields[nested_field], nested_classes):
                        msg = "'%s' is not a nested field" % nested_field
                        raise ValidationError(msg)
                allowed_nested_fields.update(field)
            else:
                # Flat field
                if field not in all_fields:
                    msg = "'%s' field is not found" % field
                    raise ValidationError(msg)
                allowed_flat_fields.append(field)
        self.nested_fields_queries = allowed_nested_fields
        
        all_allowed_fields = allowed_flat_fields + list(allowed_nested_fields)
        for field in all_fields:
            if field not in all_allowed_fields:
                fields.pop(field)

        return fields


class NestedCreateMixin(object):
    """ Create Mixin """
    def create_writable_foreignkey_related(self, data):
        # data format {field: {sub_field: value}}
        request = self.context.get("request")
        context={"request": request}
        objs = {}
        for field, value in data.items():
            # Get serializer class for nested field
            SerializerClass = type(self.get_fields()[field])
            serializer = SerializerClass(data=value, context=context)
            serializer.is_valid()
            obj = serializer.save()
            objs.update({field: obj})
        return objs

    def bulk_create_objs(self, field, data):
        request = self.context.get("request")
        context={"request": request}
        model = self.get_fields()[field].child.Meta.model
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=context)
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
    def constrain_error_prefix(self, field):
        return "Error on %s field: " % (field,)

    def update_replaceable_foreignkey_related(self, instance, data):
        # data format {field: obj}
        objs = {}
        for field, nested_obj in data.items():
            setattr(instance, field, nested_obj)
            instance.save()
            objs.update({field: instance})
        return objs

    def update_writable_foreignkey_related(self, instance, data):
        # data format {field: {sub_field: value}}
        request = self.context.get("request")
        context={"request": request}
        objs = {}
        for field, values in data.items():
            # Get serializer class for nested field
            SerializerClass = type(self.get_fields()[field])
            nested_obj = getattr(instance, field)
            serializer = SerializerClass(
                nested_obj, 
                data=values, 
                context=context,
                partial=self.partial
            )
            serializer.is_valid()
            serializer.save()
            objs.update({field: nested_obj})
        return objs

    def bulk_create_many_to_many_related(self, field, nested_obj, data):
        request = self.context.get("request")
        context={"request": request}
        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=context)
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        nested_obj.add(*pks)
        return pks

    def bulk_create_many_to_one_related(self, field, nested_obj, data):
        request = self.context.get("request")
        context={"request": request}
        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        pks = []
        for values in data:
            serializer = SerializerClass(data=values, context=context)
            serializer.is_valid()
            obj = serializer.save()
            pks.append(obj.pk)
        return pks

    def bulk_update_many_to_many_related(self, field, nested_obj, data):
        # {pk: {sub_field: values}}
        objs = []
        request = self.context.get("request")
        context={"request": request}
        # Get serializer class for nested field
        SerializerClass = type(self.get_fields()[field].child)
        for pk, values in data.items():
            obj = nested_obj.get(pk=pk)
            serializer = SerializerClass(
                obj, 
                data=values, 
                context=context, 
                partial=self.partial
            )
            serializer.is_valid()
            obj = serializer.save()
            objs.append(obj)
        return objs

    def bulk_update_many_to_one_related(self, field, instance, data):
        # {pk: {sub_field: values}}
        objs = []
        request = self.context.get("request")
        context={"request": request}
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
                context=context, 
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