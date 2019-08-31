from django_filters import rest_framework as filters

from rest_framework.serializers import ValidationError
from .parser import Parser


class CustomFilterBackend(filters.DjangoFilterBackend):
    query_param_name = "query"

    def get_filterset_kwargs(self, request, queryset, view):
        query = request.query_params.get(self.query_param_name, None)

        params = {}
        if query is not None:
            parser = Parser(query)
            try:
                parsed = parser.get_parsed()
                params = parsed["arguments"]  
            except SyntaxError:
                parsed = {}

        all_params = {**request.query_params.dict(), **params}
        return {
            'data': all_params,
            'queryset': queryset,
            'request': request,
        }
