import re
import json

import dictfier
from rest_framework import serializers
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


def get_formatted_query(raw_query, schema):
    fields = []
    for field in raw_query:
        if isinstance(field, dict):
            for nested_field in field:
                if isinstance(schema[nested_field], serializers.ListSerializer):
                    # Iterable nested field
                    nested_iterable_node = get_formatted_query(
                        field[nested_field],
                        schema[nested_field]
                    )
                    fields.append({nested_field: [nested_iterable_node]})
                else:
                    # Flat nested field
                    nested_flat_node = get_formatted_query(
                        field[nested_field],
                        schema[nested_field]
                    )
                    fields.append({nested_field: nested_flat_node})
        else:
            # Flat field
            fields.append(field)
    return fields


def parse_query(query_str):
    # Match field, '{', '}' and ','
    regax = r"[\{\}\,]|\w+"
    query_nodes = re.findall(regax, query_str)
    raw_json = []
    for i, node in enumerate(query_nodes):
        if node == "{":
            if i == 0:
                prev = '"result"'
            else:
                prev = raw_json.pop()
            raw_json.append("{" + prev + ":" + "[")
        elif node == "}":
            raw_json.append("]}")
        elif node == ",":
            raw_json.append(node)
        else:
            raw_json.append('"'+node+'"')

    json_string = "".join(raw_json)
    raw_query = json.loads(json_string)["result"]
    return raw_query


class DynamicFieldsMixin():
    query_param_name = "query"

    def list(self, request):
        schema = self.get_serializer().get_fields()
        queryset = self.get_queryset()
        if self.filter_backends is not None:
            queryset = self.filter_queryset(queryset)
        if self.pagination_class is not None:
            queryset = self.paginate_queryset(queryset)

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={'request': request}
        )

        response = Response
        if self.paginator is not None:
            response = self.get_paginated_response

        if self.query_param_name in request.query_params:
            query_str = request.query_params[self.query_param_name]
            raw_query = parse_query(query_str)
            query = get_formatted_query(raw_query, schema)
            query = [query]  # extra [] because a list is returned in this case
            data = dictfier.filter(
                serializer.data,
                query
            )
            return response(data)
        return response(serializer.data)

    def retrieve(self, request, pk=None):
        schema = self.get_serializer().get_fields()
        queryset = self.get_queryset()
        object = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(
            object, context={'request': request}
        )

        if self.query_param_name in request.query_params:
            query_str = request.query_params[self.query_param_name]
            raw_query = parse_query(query_str)

            query = get_formatted_query(raw_query, schema)
            data = dictfier.filter(
                serializer.data,
                query
            )
            return Response(data)
        return Response(serializer.data)
