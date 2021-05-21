from rest_framework import serializers
from tests.testapp.models import Genre, Book, Course, Student, Phone

from django_restql.fields import NestedField, DynamicSerializerMethodField
from django_restql.mixins import DynamicFieldsMixin
from django_restql.serializers import NestedModelSerializer


######## Serializers for Data Querying And Mutations Testing ##########
class GenreSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    class Meta:
        model = Genre
        fields = ['title', 'description']


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


class CourseWithDisableDynamicFieldsKwargSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    books = BookSerializer(many=True, read_only=True, disable_dynamic_fields=True)

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


class CourseWithAliasedBooksSerializer(CourseSerializer):
    tomes = BookSerializer(source="books", many=True, read_only=True)

    class Meta:
        model = Course
        fields = ['name', 'code', 'tomes']


class CourseWithDynamicSerializerMethodField(CourseSerializer):
    tomes = DynamicSerializerMethodField()
    related_books = DynamicSerializerMethodField()

    class Meta:
        model = Course
        fields = ['name', 'code', 'tomes', 'related_books']

    def get_tomes(self, obj, parsed_query):
        books = obj.books.all()
        serializer = BookSerializer(
            books, parsed_query=parsed_query, many=True, read_only=True
        )
        return serializer.data

    def get_related_books(self, obj, parsed_query):
        books = obj.books.all()
        query = "{title}"
        serializer = BookSerializer(
            books, query=query, many=True, read_only=True
        )
        return serializer.data


class StudentSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    course = CourseSerializer(many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']


class StudentWithAliasSerializer(DynamicFieldsMixin, serializers.ModelSerializer):
    program = CourseSerializer(source="course", many=False, read_only=True)
    phone_numbers = PhoneSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['name', 'age', 'program', 'phone_numbers']


############### Serializers for Nested Data Mutation Testing ##############
class WritableBookSerializer(DynamicFieldsMixin, NestedModelSerializer):
    genre = NestedField(GenreSerializer, many=False, required=False, allow_null=True, accept_pk=True)

    class Meta:
        model = Book
        fields = ['title', 'author', 'genre']


class WritableCourseSerializer(DynamicFieldsMixin, NestedModelSerializer):
    books = NestedField(WritableBookSerializer, many=True, required=False)

    class Meta:
        model = Course
        fields = ['name', 'code', 'books']


class ReplaceableStudentSerializer(DynamicFieldsMixin, NestedModelSerializer):
    course = NestedField(WritableCourseSerializer, accept_pk=True, allow_null=True, required=False)
    phone_numbers = PhoneSerializer(many=True, read_only=True)

    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']


class ReplaceableStudentWithAliasSerializer(DynamicFieldsMixin, NestedModelSerializer):
    full_name = serializers.CharField(source="name")
    program = NestedField(WritableCourseSerializer, source="course", accept_pk_only=True, allow_null=True, required=False)
    contacts = NestedField(PhoneSerializer, source="phone_numbers", many=True, required=False)

    class Meta:
        model = Student
        fields = ['full_name', 'age', 'program', 'contacts']


class WritableStudentSerializer(DynamicFieldsMixin, NestedModelSerializer):
    course = NestedField(WritableCourseSerializer, allow_null=True, required=False)
    phone_numbers = NestedField(PhoneSerializer, many=True, required=False)

    class Meta:
        model = Student
        fields = ['name', 'age', 'course', 'phone_numbers']


class WritableStudentWithAliasSerializer(DynamicFieldsMixin, NestedModelSerializer):
    program = NestedField(WritableCourseSerializer, source="course", allow_null=True, required=False)
    contacts = NestedField(PhoneSerializer, source="phone_numbers", many=True, required=False)

    class Meta:
        model = Student
        fields = ['name', 'age', 'program', 'contacts']
