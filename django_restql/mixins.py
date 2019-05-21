import json

import dictfier
from rest_framework.response import Response
from django.shortcuts import get_object_or_404

def format_query(query, schema):
    for field in query:
        if isinstance(field, dict):
            for nested_field in field:
                if isinstance(schema[nested_field], list):
                    # Iterable nested field
                    field[nested_field] = [field[nested_field]]
                    format_query(schema[nested_field], field[nested_field][0])
                else:
                    # Flat nested field
                    format_query(schema[nested_field], field[nested_field])
        else:
            pass

class DynamicFieldsMixin():
    query_param_name = "query"

    def list(self, request):
        schema = self.get_serializer().data
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
            query = json.loads(request.query_params[self.query_param_name])

            format_query(query, schema)
            query = [query]
            data = dictfier.filter(
                serializer.data,
                query
            )

            return response(data)
        return response(serializer.data)

    def retrieve(self, request, pk=None):
        schema = self.get_serializer().data
        queryset = self.get_queryset()
        object = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(
            object, context={'request': request}
        )

        if self.query_param_name in request.query_params:
            query = json.loads(request.query_params[self.query_param_name])

            format_query(query, schema)
            data = dictfier.filter(
                serializer.data,
                query
            )
            return Response(data)
        return Response(serializer.data)
