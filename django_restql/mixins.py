import json
import warnings

import dictfier

class DynamicFieldsMixin():
    query_param_name = "query"

    def flat_obj(self, obj, parent_obj):
        if isinstance(obj, (str, int, bool, float)):
            return obj
        elif type(obj).__name__ == "ManyRelatedManager":
            return [sub_obj.pk for sub_obj in obj.all()]
        elif type(obj).__name__ == "RelatedManager":
            return [sub_obj.pk for sub_obj in obj.all()]
        else:
            return obj.pk

    def nested_flat_obj(self, obj, parent_obj):
        return obj

    def nested_iter_obj(self, obj, parent_obj):
        if type(obj).__name__ == "ManyRelatedManager":
            return obj.all()
        elif type(obj).__name__ == "RelatedManager":
            return obj.all()
        else:
            return obj

    def to_representation(self, instance):
        try:
            request = self.context['request']
        except KeyError:
            conf = getattr(settings, 'DRF_DYNAMIC_FIELDS', {})
            if not conf.get('SUPPRESS_CONTEXT_WARNING', False) is True:
                warnings.warn('Context does not have access to request.')
            return super().to_representation(instance)

        if self.query_param_name in request.query_params:
            query = json.loads(request.query_params[self.query_param_name])
            data = dictfier.dictfy(
                instance, 
                query,
                flat_obj=self.flat_obj,
                nested_flat_obj=self.nested_flat_obj,
                nested_iter_obj=self.nested_iter_obj,
            )
            return data
        else:
            return super().to_representation(instance)
