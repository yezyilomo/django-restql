from rest_framework import serializers
from django_restql.mixins import DynamicFieldsMixin
from tests.testapp.models import Book, Course, Student, Phone

class BookSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['id', 'title', 'author']


class CourseSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class PhoneSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = ['number', 'type']

class StudentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']
