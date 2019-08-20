import re
import json

from rest_framework.serializers import Serializer, ListSerializer, ValidationError


class DynamicFieldsMixin(object):
    query_param_name = "query"

    def has_query_param(self, request):
        return self.query_param_name in request.query_params

    def get_query_str(self, request):
        return request.query_params[self.query_param_name]

    @staticmethod
    def parse_query(query_str):
        # Match invalid chars i.e non alphanumerics
        # Except '{', ',', ' ' and '}'
        invalid_chars_regex = r"[^\{\}\,\w\s]"
        invalid_chars = re.findall(invalid_chars_regex, query_str)
        if invalid_chars:
            invalid_chars_str = ", ".join(set(invalid_chars))
            msg = "query should not contain %s characters" % invalid_chars_str
            raise ValidationError(msg)

        # Match valid query e.g {id, name, location{country, city}}
        valid_nodes_regex = r"[\{\}\,]|\w+"
        valid_nodes = re.findall(valid_nodes_regex, query_str)
        query_nodes = []
        for i, node in enumerate(valid_nodes):
            if node == "{":
                if i == 0:
                    key = '"result"'
                else:
                    key = query_nodes.pop()
                query_nodes.append("{" + key + ":" + "[")
            elif node == ",":
                query_nodes.append(node)
            elif node == "}":
                query_nodes.append("]}")
            else:
                query_nodes.append('"'+node+'"')

        nodes_string = "".join(query_nodes)
        try:
            raw_query = json.loads(nodes_string)["result"]
        except ValueError:
            msg = "query parameter is not formatted properly"
            raise ValidationError(msg)
        return raw_query

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
                allowed_fields = self.parse_query(query_str)
        elif isinstance(self.parent, ListSerializer):
            source = self.parent.source
            parent = self.parent.parent
            allowed_fields = []
            if hasattr(parent, "allowed_fields"):
                allowed_fields = parent.allowed_fields[source]
        elif isinstance(self.parent, Serializer):
            source = self.source
            parent = self.parent
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
