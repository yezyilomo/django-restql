from rest_framework import viewsets
from rest_framework.response import Response
from django_restql.mixins import DynamicFieldsMixin

from tests.testapp.models import Book, Course, Student
from tests.testapp.serializers import (
	BookSerializer, CourseSerializer, StudentSerializer,
	CourseWithFieldsKwargSerializer, CourseWithExcludeKwargSerializer,
	CourseWithReturnPkkwargSerializer
)

class BookViewSet(viewsets.ModelViewSet):
	serializer_class = BookSerializer
	queryset = Book.objects.all()
	filter_fields = ("id",)


class CourseViewSet(viewsets.ModelViewSet):
	serializer_class = CourseSerializer
	queryset = Course.objects.all()

class CourseWithReturnPkkwargViewSet(viewsets.ModelViewSet):
	serializer_class = CourseWithReturnPkkwargSerializer
	queryset = Course.objects.all()

class CourseWithFieldsKwargViewSet(viewsets.ModelViewSet):
	serializer_class = CourseWithFieldsKwargSerializer
	queryset = Course.objects.all()

class CourseWithExcludeKwargViewSet(viewsets.ModelViewSet):
	serializer_class = CourseWithExcludeKwargSerializer
	queryset = Course.objects.all()

class StudentViewSet(viewsets.ModelViewSet):
	serializer_class = StudentSerializer
	queryset = Student.objects.all()
