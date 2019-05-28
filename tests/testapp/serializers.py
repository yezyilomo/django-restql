from rest_framework import serializers
from tests.testapp.models import Book, Course, Student, Phone

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author']


class CourseSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class PhoneSerializer(serializers.ModelSerializer):
    class Meta:
        model = Phone
        fields = ['number', 'type']

class StudentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)
    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']
