from rest_framework.serializers import ModelSerializer

from .mixins import NestedCreateMixin, NestedUpdateMixin, DynamicFieldsMixin

class NestedModelSerializer(
        NestedCreateMixin, 
        NestedUpdateMixin, 
        ModelSerializer):
    pass
