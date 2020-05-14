# Settings
Configuration for **Django RESTQL** is all namespaced inside a single Django setting named `RESTQL`, below is a list of what you can configure under `RESTQL` setting.

## QUERY_PARAM_NAME
The default value for this is `query`. If you don't want to use the name `query` as your parameter, you can change it with`QUERY_PARAM_NAME` on settings file e.g
```py
RESTQL = {
    'QUERY_PARAM_NAME': 'your_favourite_name'
}
```
Now you can use the name `your_favourite_name` as your query parameter. E.g

`GET /users/?your_favourite_name={id, username}`

## AUTO_APPLY_EAGER_LOADING
The default value for this is `True`. When using the `EagerLoadingMixin`, this setting controls if the mappings for `select_related` and `prefetch_related` are applied automatically when calling `get_queryset`. To turn it off, set the `AUTO_APPLY_EAGER_LOADING` setting or `auto_apply_eager_loading` attribute on the view to `False`.
```py
# settings.py file
# This will turn off auto apply eager loading globally
RESTQL = {
    'AUTO_APPLY_EAGER_LOADING': False
}
```

If auto apply eager loading is turned off, the method `apply_eager_loading` can still be used on your queryset if you wish to select or prefetch related fields according to your conditions, For example you can check if there was a query parameter passed in by using `has_restql_query_param`, if true then apply eager loading otherwise return a normal queryset.
```py
from rest_framework import viewsets
from django_restql.mixins import EagerLoadingMixin
from myapp.serializers import StudentSerializer
from myapp.models import Student

class StudentViewSet(EagerLoadingMixin, viewsets.ModelViewSet):
	serializer_class = StudentSerializer
	queryset = Student.objects.all()

    # Turn off auto apply eager loading per view
    # This overrides the `AUTO_APPLY_EAGER_LOADING` setting on this view
    auto_apply_eager_loading = False
    select_related = {
		"program": "course"
	}
	prefetch_related = {
		"program.books": "course__books"
	}

	def get_queryset(self):
	    queryset = super().get_queryset()
	    if self.has_restql_query_param:
	        queryset = self.apply_eager_loading(queryset)
        return queryset
```
