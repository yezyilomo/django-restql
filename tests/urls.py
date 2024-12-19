"""test_app URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/2.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

try:
    # For django <= 3.x
    from django.conf.urls import include, url as path
except ImportError:
    from django.urls import include, path

from tests.testapp import views

from rest_framework import routers

router = routers.DefaultRouter()

router.register("books", views.BookViewSet, "book")
router.register("courses", views.CourseViewSet, "course")
router.register(
    "courses-with-disable-dynamic-fields",
    views.CourseWithDisableDaynamicFieldsKwargViewSet,
    "course_with_disable_dynamic_fields_kwarg",
)
router.register(
    "courses-with-returnpk-kwarg",
    views.CourseWithReturnPkkwargViewSet,
    "course_with_returnpk_kwarg",
)
router.register(
    "courses-with-field-kwarg",
    views.CourseWithFieldsKwargViewSet,
    "course_with_field_kwarg",
)
router.register(
    "courses-with-exclude-kwarg",
    views.CourseWithExcludeKwargViewSet,
    "course_with_exclude_kwarg",
)
router.register(
    "courses-with-aliased-books",
    views.CourseWithAliasedBooksViewSet,
    "course_with_aliased_books",
)
router.register(
    "course-with-dynamic-serializer-method-field",
    views.CourseWithDynamicSerializerMethodFieldViewSet,
    "course_with_dynamic_serializer_method_field",
)
router.register("students", views.StudentViewSet, "student")
router.register(
    "students-eager-loading", views.StudentEagerLoadingViewSet, "student_eager_loading"
)
router.register(
    "students-eager-loading-prefetch",
    views.StudentEagerLoadingPrefetchObjectViewSet,
    "student_eager_loading_prefetch",
)
router.register(
    "students-auto-apply-eager-loading",
    views.StudentAutoApplyEagerLoadingViewSet,
    "student_auto_apply_eager_loading",
)

router.register("writable-courses", views.WritableCourseViewSet, "wcourse")
router.register("replaceable-students", views.ReplaceableStudentViewSet, "rstudent")
router.register(
    "replaceable-students-with-alias",
    views.ReplaceableStudentWithAliasViewSet,
    "rstudent_with_alias",
)
router.register("writable-students", views.WritableStudentViewSet, "wstudent")
router.register(
    "writable-students-with-alias",
    views.WritableStudentWithAliasViewSet,
    "wstudent_with_alias",
)
router.register("posts", views.PostViewSet, "post")

urlpatterns = [path("", include(router.urls))]
