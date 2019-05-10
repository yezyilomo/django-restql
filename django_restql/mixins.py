import json
import datetime
import warnings

import dictfier

class DynamicFieldsMixin():
    query_param_name = "query"

    def flat_field(self, obj, parent_obj):
        if isinstance(obj, (str, int, bool, float)):
            return obj
        if isinstance(obj, datetime.datetime):
            return obj.strftime("%Y-%m-%d-%H-%M")
        if isinstance(obj, datetime.date):
            return obj.strftime("%Y-%m-%d")
        if isinstance(obj, datetime.time):
            return obj.strftime("%H-%M-%S")
        cls_name = obj.__class__.__name__
        if cls_name in ("ManyRelatedManager", "RelatedManager"):
            return [sub_obj.pk for sub_obj in obj.all()]
        if hasattr(obj, "pk"):
            return obj.pk
        raise ValueError(
            "django-restql failed to serialize an object of type '%s'" 
            % cls_name
        )

    def nested_flat_field(self, obj, parent_obj):
        return obj

    def nested_iter_field(self, obj, parent_obj):
        cls_name = obj.__class__.__name__
        if cls_name in ("ManyRelatedManager", "RelatedManager"):
            return obj.all()
        return obj

    def to_representation(self, instance):
        try:
            request = self.context['request']
        except KeyError:
            warnings.warn('Context does not have access to request.')
            return super().to_representation(instance)

        if self.query_param_name in request.query_params:
            query = json.loads(request.query_params[self.query_param_name])
            data = dictfier.dictfy(
                instance, 
                query,
                flat_obj=self.flat_field,
                nested_flat_obj=self.nested_flat_field,
                nested_iter_obj=self.nested_iter_field,
            )
            return data
            
        return super().to_representation(instance)
