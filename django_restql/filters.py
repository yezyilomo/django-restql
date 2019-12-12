from .parser import Parser
from .settings import restql_settings
from .exceptions import QueryFormatError
from .mixins import RequestQueryParserMixin


BASE_FILTER_BACKEND = getattr(
    restql_settings,
    'DEFAULT_BASE_FILTER_BACKEND'
)


class RESTQLFilterBackendMixin(RequestQueryParserMixin):
    def get_parsed_restql_query(self, request):
        if self.has_restql_query_param(request):
            try:
                return self.get_parsed_restql_query_from_req(request)
            except (SyntaxError, QueryFormatError):
                pass

        query = {
            "include": ["*"],
            "exclude": [],
            "arguments": {}
        }
        return query

    def build_filter_params(self, parsed_query, parent=None):
        filter_params = {}
        prefix = ''
        if parent is None:
            filter_params.update(parsed_query['arguments'])
        else:
            prefix = parent + '__'
            for argument, value in parsed_query['arguments'].items():
                name = prefix + argument
                filter_params.update({
                    name: value
                })
        for field in parsed_query['include']:
            if isinstance(field, dict):
                for sub_field, sub_parsed_query in field.items():
                    nested_filter_params = self.build_filter_params(
                        sub_parsed_query,
                        parent=prefix + sub_field
                    )
                    filter_params.update(nested_filter_params)
        return filter_params

    def get_filter_params(self, request):
        parsed = self.get_parsed_restql_query(request)
        filter_params = self.build_filter_params(parsed)
        return filter_params


class RESTQLFilterBackend(RESTQLFilterBackendMixin, BASE_FILTER_BACKEND):
    def get_filterset_kwargs(self, request, queryset, view):
        filter_params = self.get_filter_params(request)

        return {
            'data': filter_params,
            'queryset': queryset,
            'request': request
        }