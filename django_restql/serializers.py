from rest_framework.serializers import ModelSerializer

from .mixins import NestedCreateMixin, NestedUpdateMixin


class NestedModelSerializer(
        NestedCreateMixin,
        NestedUpdateMixin,
        ModelSerializer):
    pass
