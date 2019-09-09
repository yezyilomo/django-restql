from rest_framework import serializers
from tests.testapp.models import Book, Course, Student, Phone
from django_restql.fields import  NestedField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer


######## Serializers for Data Querying And Mutations Testing ##########
class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author']


class PhoneSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = ['number', 'type', 'student']


################# Serializers for Data Querying Testing ################
class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class CourseWithReturnPkkwargSerializer(CourseSerializer):
    books = BookSerializer(many=True, read_only=True, return_pk=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class CourseWithFieldsKwargSerializer(CourseSerializer):
    books = BookSerializer(many=True, read_only=True, fields=["title"])
    class Meta(CourseSerializer.Meta):
        pass


class CourseWithExcludeKwargSerializer(CourseSerializer):
    books = BookSerializer(many=True, read_only=True, exclude=["author"])
    class Meta(CourseSerializer.Meta):
        pass


class StudentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']


############### Serializers for Nested Data Mutation Testing ##############
class WritableCourseSerializer(NestedModelSerializer):
    books = NestedField(BookSerializer, many=True, required=False)
        
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class ReplaceableCourseSerializer(NestedModelSerializer):
    books = NestedField(BookSerializer, accept_pk=True, many=True, required=False)
        
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class ReplaceableStudentSerializer(NestedModelSerializer):
    course = NestedField(WritableCourseSerializer, accept_pk=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']


class WritableStudentSerializer(NestedModelSerializer):
    course = NestedField(WritableCourseSerializer)
    phone_numbers = NestedField(PhoneSerializer, many=True, required=False)

    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']
