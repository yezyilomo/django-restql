import json

import dictfier
from rest_framework.response import Response
from django.shortcuts import get_object_or_404


class DynamicFieldsMixin():
    query_param_name = "query"

    def list(self, request):
        queryset = self.get_queryset()
        filtered_queryset = self.filter_queryset(queryset)
        paginated_queryset = self.paginate_queryset(filtered_queryset)
        serializer = self.get_serializer(
            paginated_queryset, many=True, context={'request': request}
        )

        if self.query_param_name in request.query_params:
            query = json.loads(request.query_params[self.query_param_name])

            data = dictfier.filter(
                serializer.data,
                query
            )
            return self.get_paginated_response(data)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        queryset = self.get_queryset()
        object = get_object_or_404(queryset, pk=pk)
        serializer = self.get_serializer(
            object, context={'request': request}
        )

        if self.query_param_name in request.query_params:
            query = json.loads(request.query_params[self.query_param_name])

            data = dictfier.filter(
                serializer.data,
                query
            )
            return Response(data)
        return Response(serializer.data)
