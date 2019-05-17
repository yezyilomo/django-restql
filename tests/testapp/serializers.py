from rest_framework import serializers
from tests.testapp.models import Book, Course, Student

class BookSerializer(serializers.ModelSerializer):
    class Meta:
        model = Book
        fields = ['title', 'author']


class CourseSerializer(serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=False)
    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class StudentSerializer(serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=False)
    class Meta:
        model = Student
        fields = ['name', 'age', 'course']

