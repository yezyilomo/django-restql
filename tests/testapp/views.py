from django.db.models import Prefetch
from rest_framework import viewsets

from tests.testapp.models import Book, Course, Student, Phone, Post
from tests.testapp.serializers import (
    BookSerializer,
    CourseSerializer,
    StudentSerializer,
    CourseWithFieldsKwargSerializer,
    CourseWithExcludeKwargSerializer,
    CourseWithReturnPkkwargSerializer,
    ReplaceableStudentSerializer,
    WritableStudentSerializer,
    WritableCourseSerializer,
    CourseWithAliasedBooksSerializer,
    CourseWithDynamicSerializerMethodField,
    StudentWithAliasSerializer,
    WritableStudentWithAliasSerializer,
    ReplaceableStudentWithAliasSerializer,
    CourseWithDisableDynamicFieldsKwargSerializer,
    PostSerializer,
)

from django_restql.mixins import EagerLoadingMixin, QueryArgumentsMixin


#### ViewSets for Data Querying And Mutations Testing ####
class BookViewSet(viewsets.ModelViewSet):
    serializer_class = BookSerializer
    queryset = Book.objects.all()


class CourseViewSet(viewsets.ModelViewSet):
    serializer_class = CourseSerializer
    queryset = Course.objects.all()


############# ViewSets For Data Querying Testing #############
class CourseWithDisableDaynamicFieldsKwargViewSet(viewsets.ModelViewSet):
    serializer_class = CourseWithDisableDynamicFieldsKwargSerializer
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


class CourseWithAliasedBooksViewSet(viewsets.ModelViewSet):
    serializer_class = CourseWithAliasedBooksSerializer
    queryset = Course.objects.all()


class CourseWithDynamicSerializerMethodFieldViewSet(viewsets.ModelViewSet):
    serializer_class = CourseWithDynamicSerializerMethodField
    queryset = Course.objects.all()


class StudentViewSet(QueryArgumentsMixin, viewsets.ModelViewSet):
    serializer_class = StudentSerializer
    queryset = Student.objects.all()

    # For django-filter <=21.1
    filter_fields = {
        "name": ["exact"],
        "age": ["exact"],
        "course__name": ["exact"],
        "course__code": ["exact"],
        "course__books__title": ["exact"],
        "course__books__author": ["exact"],
    }

    # For django-filter > 21.1
    filterset_fields = {
        "name": ["exact"],
        "age": ["exact"],
        "course__name": ["exact"],
        "course__code": ["exact"],
        "course__books__title": ["exact"],
        "course__books__author": ["exact"],
    }


class StudentEagerLoadingViewSet(EagerLoadingMixin, viewsets.ModelViewSet):
    serializer_class = StudentWithAliasSerializer
    queryset = Student.objects.all()
    select_related = {"program": "course"}
    prefetch_related = {
        "phone_numbers": "phone_numbers",
        "program.books": "course__books",
    }


class StudentEagerLoadingPrefetchObjectViewSet(
    EagerLoadingMixin, viewsets.ModelViewSet
):
    serializer_class = StudentWithAliasSerializer
    queryset = Student.objects.all()
    select_related = {"program": "course"}
    prefetch_related = {
        "phone_numbers": [
            Prefetch("phone_numbers", queryset=Phone.objects.all()),
        ],
        "program.books": Prefetch("course__books", queryset=Book.objects.all()),
    }


class StudentAutoApplyEagerLoadingViewSet(EagerLoadingMixin, viewsets.ModelViewSet):
    serializer_class = StudentWithAliasSerializer
    queryset = Student.objects.all()
    auto_apply_eager_loading = False
    select_related = {"program": "course"}
    prefetch_related = {
        "phone_numbers": [
            Prefetch("phone_numbers", queryset=Phone.objects.all()),
        ],
        "program.books": Prefetch("course__books", queryset=Book.objects.all()),
    }


######### ViewSets For Data Mutations Testing ##########
class WritableCourseViewSet(viewsets.ModelViewSet):
    serializer_class = WritableCourseSerializer
    queryset = Course.objects.all()


class ReplaceableStudentViewSet(viewsets.ModelViewSet):
    serializer_class = ReplaceableStudentSerializer
    queryset = Student.objects.all()


class ReplaceableStudentWithAliasViewSet(viewsets.ModelViewSet):
    serializer_class = ReplaceableStudentWithAliasSerializer
    queryset = Student.objects.all()


class WritableStudentViewSet(viewsets.ModelViewSet):
    serializer_class = WritableStudentSerializer
    queryset = Student.objects.all()


class WritableStudentWithAliasViewSet(viewsets.ModelViewSet):
    serializer_class = WritableStudentWithAliasSerializer
    queryset = Student.objects.all()


class PostViewSet(viewsets.ModelViewSet):
    serializer_class = PostSerializer
    queryset = Post.objects.all()
