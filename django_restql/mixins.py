import re
import json

import dictfier
from django.shortcuts import get_object_or_404
from rest_framework.response import Response
from rest_framework.serializers import Serializer, ListSerializer

from .exceptions import InvalidField, FieldNotFound, FormatError


class Query(object):
    def __init__(self, query_str, schema):
        self.query_str = query_str
        self.schema = schema

    def parse(self):
        parsed_query = self._parsed_query(self.query_str)
        return self._formatted_query(parsed_query, self.schema)

    @staticmethod
    def _parsed_query(query_str):
        # Match invalid chars i.e non alphanumerics
        # Except '{', ',', ' ' and '}'
        invalid_chars_regex = r"[^\{\}\,\w\s]"
        invalid_chars = re.findall(invalid_chars_regex, query_str)
        if invalid_chars:
            invalid_chars_str = ", ".join(set(invalid_chars))
            msg = "query should not contain %s characters" % invalid_chars_str
            raise FormatError(msg)

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
            raise FormatError(msg)
        return raw_query

    @classmethod
    def _formatted_query(cls, raw_query, schema):
        query = []
        for field in raw_query:
            if isinstance(field, dict):
                for nested_field in field:
                    if nested_field not in schema:
                        msg = "'%s' field is not found" % nested_field
                        raise FieldNotFound(msg)

                    nested_schema = schema[nested_field]
                    if isinstance(nested_schema, ListSerializer):
                        # Iterable nested field
                        nested_iterable_node = cls._formatted_query(
                            field[nested_field],
                            nested_schema.child.get_fields()
                        )
                        query.append({nested_field: [nested_iterable_node]})

                    elif isinstance(nested_schema, Serializer):
                        # Flat nested field
                        nested_flat_node = cls._formatted_query(
                            field[nested_field],
                            nested_schema.get_fields()
                        )
                        query.append({nested_field: nested_flat_node})

                    else:
                        msg = "'%s' is not a nested field" % nested_field
                        raise InvalidField(msg)
            else:
                # Flat field
                if field not in schema:
                    msg = "'%s' field is not found" % field
                    raise FieldNotFound(msg)
                query.append(field)

        return query


class DynamicFieldsMixin(object):
    query_param_name = "query"

    def tofilter(self, request):
        return self.query_param_name in request.query_params

    def get_query_str(self, request):
        return request.query_params[self.query_param_name]

    def list(self, request):
        queryset = self.get_queryset()
        if self.filter_backends is not None:
            queryset = self.filter_queryset(queryset)

        if self.pagination_class is not None:
            queryset = self.paginate_queryset(queryset)

        if self.paginator is not None:
            response = self.get_paginated_response
        else:
            response = Response

        serializer = self.get_serializer(
            queryset,
            many=True,
            context={'request': request}
        )

        if self.tofilter(request):
            query_str = self.get_query_str(request)
            schema = self.get_serializer().get_fields()
            query = Query(query_str, schema)

            try:
                parsed_query = query.parse()
            except (FormatError, InvalidField) as e:
                return Response({"error": str(e)}, 400)
            except FieldNotFound as e:
                return Response({"error": str(e)}, 404)

            # extra [] cuz a list of resources is expected
            filter_query = [parsed_query]

            filtered_data = dictfier.filter(serializer.data, filter_query)
            return response(filtered_data)

        return response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        object = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(
            object, context={'request': request}
        )

        if self.tofilter(request):
            query_str = self.get_query_str(request)

            schema = self.get_serializer().get_fields()
            query = Query(query_str, schema)

            try:
                parsed_query = query.parse()
            except (FormatError, InvalidField) as e:
                return Response({"error": str(e)}, 400)
            except FieldNotFound as e:
                return Response({"error": str(e)}, 404)

            # No extra [] cuz only one resource is expected
            filter_query = parsed_query

            filtered_data = dictfier.filter(serializer.data, filter_query)
            return Response(filtered_data)

        return Response(serializer.data)
