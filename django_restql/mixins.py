import re
import json

from rest_framework.serializers import Serializer, ListSerializer, ValidationError

from .parser import Parser


class DynamicFieldsMixin(object):
    query_param_name = "query"

    def has_query_param(self, request):
        return self.query_param_name in request.query_params

    def get_query_str(self, request):
        return request.query_params[self.query_param_name]

    @property
    def fields(self):
        fields = super().fields
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
                    parsed = parser.get_parsed()
                except SyntaxError as e:
                    raise ValidationError(str(e))
                    
                allowed_fields = parsed["fields"]
        elif isinstance(self.parent, ListSerializer):
            source = self.parent.source
            parent = self.parent.parent
            allowed_fields = []
            if hasattr(parent, "allowed_fields"):
                allowed_fields = parent.allowed_fields[source]
        elif isinstance(self.parent, Serializer):
            source = self.source
            parent = self.parent
            allowed_fields = []
            if hasattr(parent, "allowed_fields"):
                allowed_fields = parent.allowed_fields[source]
        else:
            # Unkown scenario
            return fields

        if allowed_fields is None:
            # No filtering on nested fields
            # Retrieve all nested fields
            return fields
            
        all_fields = list(fields.keys())
        allowed_fields_dict = {}
        for field in allowed_fields:
            if isinstance(field, dict):
                for nested_field in field:
                    if nested_field not in all_fields:
                        msg = "'%s' field is not found" % field
                        raise ValidationError(msg)
                    nested_classes = (Serializer, ListSerializer)
                    if not isinstance(fields[nested_field], nested_classes):
                        msg = "'%s' is not a nested field" % nested_field
                        raise ValidationError(msg)
                allowed_fields_dict.update(field)
            else:
                if field not in all_fields:
                    msg = "'%s' field is not found" % field
                    raise ValidationError(msg)
                allowed_fields_dict.update({field: None})
        self.allowed_fields = allowed_fields_dict
        
        for field in all_fields:
            if field not in allowed_fields_dict.keys():
                fields.pop(field)

        return fields
