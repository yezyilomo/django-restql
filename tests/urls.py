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

from django.conf.urls import include, url

from rest_framework import routers
from tests.testapp import views


router = routers.DefaultRouter()

router.register('books', views.BookViewSet, base_name='book')
router.register('courses', views.CourseViewSet, base_name='course')
router.register('courses-with-returnpk-kwarg', views.CourseWithReturnPkkwargViewSet, base_name='course_with_returnpk_kwarg')
router.register('courses-with-field-kwarg', views.CourseWithFieldsKwargViewSet, base_name='course_with_field_kwarg')
router.register('courses-with-exclude-kwarg', views.CourseWithExcludeKwargViewSet, base_name='course_with_exclude_kwarg')
router.register('courses-with-aliased-books', views.CourseWithAliasedBooksViewSet, base_name='course_with_aliased_books')
router.register('course-with-dynamic-serializer-method-field', views.CourseWithDynamicSerializerMethodFieldViewSet, base_name='course_with_dynamic_serializer_method_field')
router.register('students', views.StudentViewSet, base_name='student')
router.register('students-eager-loading', views.StudentEagerLoadingViewSet, base_name='student_eager_loading')
router.register('students-eager-loading-prefetch', views.StudentEagerLoadingPrefetchObjectViewSet, base_name='student_eager_loading_prefetch')
router.register('students-auto-apply-eager-loading', views.StudentAutoApplyEagerLoadingViewSet, base_name='student_auto_apply_eager_loading')

router.register('writable-courses', views.WritableCourseViewSet, base_name='wcourse')
router.register('replaceable-courses', views.ReplaceableCourseViewSet, base_name='rcourse')
router.register('replaceable-students', views.ReplaceableStudentViewSet, base_name='rstudent')
router.register('writable-students', views.WritableStudentViewSet, base_name='wstudent')

urlpatterns = [
    url('', include(router.urls))
]
