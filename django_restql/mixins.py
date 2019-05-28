import re
import json

import dictfier
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import Serializer, ListSerializer

from .exceptions import InvalidField, FieldNotFound, FormatError


def parse_query(query_str):
    invalid_chars_regax = r"[^\{\}\,\w\s]"
    invalid_chars = re.findall(invalid_chars_regax, query_str)
    if invalid_chars:
        invalid_chars =  str(set(invalid_chars))[1:-1]
        msg = "query should not contain %s characters" % invalid_chars
        raise FormatError(msg)

    # Match '{', '}', ',' and field
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
    try:
        raw_query = json.loads(json_string)["result"]
    except ValueError as e:
        msg = "query parameter is not formatted properly"
        raise FormatError(msg)
    return raw_query


def get_formatted_query(raw_query, schema):
    fields = []
    for field in raw_query:
        if isinstance(field, dict):
            for nested_field in field:
                if nested_field not in schema:
                    msg = "'%s' field is not found" % nested_field
                    raise FieldNotFound(msg)

                if isinstance(schema[nested_field], ListSerializer):
                    # Iterable nested field
                    nested_iterable_node = get_formatted_query(
                        field[nested_field],
                        schema[nested_field].child.get_fields()
                    )
                    fields.append({nested_field: [nested_iterable_node]})

                elif isinstance(schema[nested_field], Serializer):
                    # Flat nested field
                    nested_flat_node = get_formatted_query(
                        field[nested_field],
                        schema[nested_field].get_fields()
                    )
                    fields.append({nested_field: nested_flat_node})

                else:
                    msg = "'%s' is not a nested field" % nested_field
                    raise InvalidField(msg)
        else:
            # Flat field
            if field not in schema:
                msg = "'%s' field is not found" % field
                raise FieldNotFound(msg)

            fields.append(field)

    return fields


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

            try:
                raw_query = parse_query(query_str)
            except FormatError as e:
                return Response({"error": str(e)}, 400)

            try:
                query = get_formatted_query(raw_query, schema)
            except FieldNotFound as e:
                return Response({"error": str(e)}, 404)
            except InvalidField as e:
                return Response({"error": str(e)}, 400)

            # extra [] because a list is returned in this case
            query = [query]
            data = dictfier.filter(serializer.data, query)
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

            try:
                raw_query = parse_query(query_str)
            except FormatError as e:
                return Response({"error": str(e)}, 400)

            try:
                query = get_formatted_query(raw_query, schema)
            except FieldNotFound as e:
                return Response({"error": str(e)}, 404)
            except InvalidField as e:
                return Response({"error": str(e)}, 400)

            data = dictfier.filter(serializer.data, query)
            return Response(data)

        return Response(serializer.data)
