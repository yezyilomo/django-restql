from rest_framework.serializers import (
    Serializer, ListSerializer, ValidationError
)

from .parser import Parser


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
        super(DynamicFieldsMixin, self).__init__(*args, **kwargs)

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
            # Drop any fields that are not specified in the `fields` argument.
            allowed = set(self.allowed_fields)
            existing = set(fields)
            not_allowed = existing.symmetric_difference(allowed)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found"%field_name
                    raise Exception(msg) from None

        if self.excluded_fields is not None:
            # Drop any fields that are not specified in the `exclude` argument.
            not_allowed = set(self.excluded_fields)
            for field_name in not_allowed:
                try:
                    fields.pop(field_name)
                except KeyError:
                    msg = "Field `%s` is not found"%field_name
                    raise Exception(msg) from None
        return fields

    @property
    def fields(self):
        fields = self.get_allowed_fields()
        request = self.context.get('request')
        if request is None or not self.has_query_param(request):
            return fields

        is_top_retrieve_request = self.source is None and self.parent is None
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
                    msg = "Error: " + str(e.args[0]) + " after " + e.text
                    raise ValidationError(msg)
                    
        elif isinstance(self.parent, ListSerializer):
            source = self.parent.source
            parent = self.parent.parent
            fields_query = []
            if hasattr(parent, "nested_fields_queries"):
                fields_query = parent.nested_fields_queries.get(source, None)
        elif isinstance(self.parent, Serializer):
            source = self.source
            parent = self.parent
            fields_query = []
            if hasattr(parent, "nested_fields_queries"):
                fields_query = parent.nested_fields_queries.get(source, None)
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
