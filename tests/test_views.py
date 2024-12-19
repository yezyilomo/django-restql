from django.urls import reverse_lazy
from rest_framework.test import APITestCase

from tests.testapp.models import (
    Book,
    Instructor,
    Course,
    Phone,
    Student,
    Post,
    Attachment,
)
from tests.testapp.serializers import (
    WritableCourseSerializer,
    WritableStudentSerializer,
)


class DataQueryingTests(APITestCase):
    def setUp(self):
        self.book1 = Book.objects.create(
            title="Advanced Data Structures", author="S.Mobit"
        )
        self.book2 = Book.objects.create(
            title="Basic Data Structures", author="S.Mobit"
        )

        self.course = Course.objects.create(name="Data Structures", code="CS210")

        self.course.books.set([self.book1, self.book2])

        self.student = Student.objects.create(name="Yezy", age=24, course=self.course)

        self.phone1 = Phone.objects.create(
            number="076711110", type="Office", student=self.student
        )
        self.phone2 = Phone.objects.create(
            number="073008880", type="Home", student=self.student
        )

    def add_second_student(self):
        """
        Adds an additional student with their own course, course books, and phone numbers.
        """
        book1 = Book.objects.create(title="Algorithm Design", author="S.Mobit")
        book2 = Book.objects.create(title="Proving Algorithms", author="S.Mobit")

        course = Course.objects.create(name="Algorithms", code="CS260")

        course.books.set([book1, book2])

        student = Student.objects.create(name="Tyler", age=25, course=course)

        Phone.objects.create(number="075711110", type="Office", student=student)
        Phone.objects.create(number="073008880", type="Home", student=student)

        student.refresh_from_db()

        return student

    def tearDown(self):
        Book.objects.all().delete()
        Course.objects.all().delete()
        Student.objects.all().delete()

    # *************** requestless tests **************

    def test_querying_data_without_request(self):
        serializer = WritableCourseSerializer(
            self.course, query="{name, code, books{title}}"
        )

        self.assertEqual(
            serializer.data,
            {
                "name": "Data Structures",
                "code": "CS210",
                "books": [
                    {"title": "Advanced Data Structures"},
                    {"title": "Basic Data Structures"},
                ],
            },
        )

    # *************** retrieve tests **************

    def test_retrieve_with_flat_query(self):
        url = reverse_lazy("book-detail", args=[self.book1.id])
        response = self.client.get(url + "?query={title, author,}", format="json")

        self.assertEqual(
            response.data,
            {"title": "Advanced Data Structures", "author": "S.Mobit"},
        )

    def test_retrieve_with_nested_flat_query(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={name, age, course{name}}", format="json"
        )

        self.assertEqual(
            response.data,
            {"name": "Yezy", "age": 24, "course": {"name": "Data Structures"}},
        )

    def test_retrieve_with_nested_iterable_query(self):
        url = reverse_lazy("course-detail", args=[self.course.id])
        response = self.client.get(
            url + "?query={name, code, books{title}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
                "books": [
                    {"title": "Advanced Data Structures"},
                    {"title": "Basic Data Structures"},
                ],
            },
        )

    def test_retrieve_with_nested_flat_query_and_aliased_field(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={name, age, programme: course{name}}", format="json"
        )

        self.assertEqual(
            response.data,
            {"name": "Yezy", "age": 24, "programme": {"name": "Data Structures"}},
        )

    def test_retrieve_with_nested_iterable_query_and_aliased_field(self):
        url = reverse_lazy("course-detail", args=[self.course.id])
        response = self.client.get(
            url + "?query={name, code, readings: books{bookTitle: title}}",
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
                "readings": [
                    {"bookTitle": "Advanced Data Structures"},
                    {"bookTitle": "Basic Data Structures"},
                ],
            },
        )

    def test_retrieve_with_disable_dynamic_fields_enabled(self):
        url = reverse_lazy(
            "course_with_disable_dynamic_fields_kwarg-detail", args=[self.course.id]
        )
        response = self.client.get(
            url + "?query={name, code, books{title}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
                "books": [
                    {"title": "Advanced Data Structures", "author": "S.Mobit"},
                    {"title": "Basic Data Structures", "author": "S.Mobit"},
                ],
            },
        )

    def test_retrieve_reverse_relation_with_nested_iterable_query(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={name, age, phone_numbers{number}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
            },
        )

    def test_retrieve_with_exclude_operator_applied_at_the_top_level(self):
        url = reverse_lazy("course-detail", args=[self.course.id])
        response = self.client.get(url + "?query={-books}", format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
            },
        )

    def test_retrieve_with_exclude_operator_applied_on_a_nested_field(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={name age phone_numbers{-number -student}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "phone_numbers": [{"type": "Office"}, {"type": "Home"}],
            },
        )

    def test_retrieve_with_exclude_operator_applied_with_include_all_operator(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={*, -course, phone: phone_numbers{-number, -student}}",
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "phone": [{"type": "Office"}, {"type": "Home"}],
            },
        )

    def test_retrieve_with_exclude_operator_applied_on_including_and_excluding_query(
        self,
    ):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={-course, studentAge : age, phone: phone_numbers{type}}",
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "studentAge": 24,
                "phone": [{"type": "Office"}, {"type": "Home"}],
            },
        )

    def test_retrieve_with_exclude_operator_applied_at_the_top_level_and_expand_a_nested_field(
        self,
    ):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={-age, -course, phone_numbers{number}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
            },
        )

    def test_retrieve_with_include_all_operator_applied_at_the_top_level_and_expand_a_nested_field(
        self,
    ):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={*, phone_numbers{-type, -student}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                },
                "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
            },
        )

    def test_retrieve_with_exclude_operator_and_include_all_operator_applied_at_the_top_level(
        self,
    ):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(
            url + "?query={*, -age, phone_numbers{-type, -student}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                },
                "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
            },
        )

    def test_retrieve_with_exclude_and_include_all_operators_being_a_little_forgiving_on_the_syntax(
        self,
    ):
        url = reverse_lazy("student-detail", args=[self.student.id])
        # We could remove `age` field and * under `phone_numbers` field and get the same results
        response = self.client.get(
            url + "?query={*, age, phone_numbers{*,-type, -student}}", format="json"
        )

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                },
                "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
            },
        )

    def test_retrieve_without_query_param(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_retrieve_eager_loading_view_mixin(self):
        """
        Ensure that we apply our prefetching or joins when we explicitly ask for fields in the
        mapping.
        """
        non_mixin_url = reverse_lazy("student-detail", args=[self.student.id])
        mixin_url = reverse_lazy("student_eager_loading-detail", args=[self.student.id])

        # Will need to fetch the course and books on serialization.
        with self.assertNumQueries(3):
            response = self.client.get(
                non_mixin_url + "?query={name, age, course{name, books}}", format="json"
            )
            self.assertEqual(
                response.data,
                {
                    "name": "Yezy",
                    "age": 24,
                    "course": {
                        "name": "Data Structures",
                        "books": [
                            {"title": "Advanced Data Structures", "author": "S.Mobit"},
                            {"title": "Basic Data Structures", "author": "S.Mobit"},
                        ],
                    },
                },
            )

        # Should select_related the course and prefetch the books.
        with self.assertNumQueries(2):
            response = self.client.get(
                mixin_url + "?query={name, age, program{name, books}}", format="json"
            )
            self.assertEqual(
                response.data,
                {
                    "name": "Yezy",
                    "age": 24,
                    "program": {
                        "name": "Data Structures",
                        "books": [
                            {"title": "Advanced Data Structures", "author": "S.Mobit"},
                            {"title": "Basic Data Structures", "author": "S.Mobit"},
                        ],
                    },
                },
            )

    def test_retrieve_eager_loading_view_mixin_ignored(self):
        """
        Ensure that we do not apply our joining/prefetching if the mapped fields aren't present.
        """
        url = reverse_lazy("student_eager_loading-detail", args=[self.student.id])

        # Make sure that no additional prefetching or select_related are run if we don't ask for
        # nested values.
        with self.assertNumQueries(1):
            response = self.client.get(url + "?query={name, age}", format="json")
            self.assertEqual(
                response.data,
                {
                    "name": "Yezy",
                    "age": 24,
                },
            )

    def test_retrieve_eager_loading_view_mixin_implicit(self):
        """
        Test that we implicitly apply our nested prefetching, since the field is present.
        """
        url = reverse_lazy("student_eager_loading-detail", args=[self.student.id])

        # This would be 3 without doing a select_related.
        with self.assertNumQueries(2):
            response = self.client.get(
                url + "?query={name, age, program}", format="json"
            )
            self.assertEqual(
                response.data,
                {
                    "name": "Yezy",
                    "age": 24,
                    "program": {
                        "name": "Data Structures",
                        "code": "CS210",
                        "books": [
                            {"title": "Advanced Data Structures", "author": "S.Mobit"},
                            {"title": "Basic Data Structures", "author": "S.Mobit"},
                        ],
                    },
                },
            )

    def test_retrieve_eager_loading_view_mixin_all_exclude(self):
        """
        Test that we implicitly apply our prefetching with * and exclusion.
        """
        url = reverse_lazy("student_eager_loading-detail", args=[self.student.id])

        # This would be 3 without doing a select_related.
        with self.assertNumQueries(2):
            response = self.client.get(
                url + "?query={*, -phone_numbers, program{*, books{title}}}",
                format="json",
            )
            self.assertEqual(
                response.data,
                {
                    "name": "Yezy",
                    "age": 24,
                    "program": {
                        "name": "Data Structures",
                        "code": "CS210",
                        "books": [
                            {"title": "Advanced Data Structures"},
                            {"title": "Basic Data Structures"},
                        ],
                    },
                },
            )

    # *************** list tests **************

    def test_list_with_flat_query(self):
        url = reverse_lazy("book-list")
        response = self.client.get(url + "?query={title, author}", format="json")

        self.assertEqual(
            response.data,
            [
                {"title": "Advanced Data Structures", "author": "S.Mobit"},
                {"title": "Basic Data Structures", "author": "S.Mobit"},
            ],
        )

    def test_list_with_nested_flat_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + "?query={name, age, course{name}}", format="json"
        )

        self.assertEqual(
            response.data,
            [{"name": "Yezy", "age": 24, "course": {"name": "Data Structures"}}],
        )

    def test_list_with_nested_iterable_query(self):
        url = reverse_lazy("course-list")
        response = self.client.get(
            url + "?query={name, code, books{title}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_reverse_relation_with_nested_iterable_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + "?query={name, age, phone_numbers{number}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "phone_numbers": [{"number": "076711110"}, {"number": "073008880"}],
                }
            ],
        )

    def test_list_with_nested_flat_and_deep_iterable_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + "?query={name, age, course{name, books{title}}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "course": {
                        "name": "Data Structures",
                        "books": [
                            {"title": "Advanced Data Structures"},
                            {"title": "Basic Data Structures"},
                        ],
                    },
                }
            ],
        )

    def test_list_without_query_param(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "course": {
                        "name": "Data Structures",
                        "code": "CS210",
                        "books": [
                            {"title": "Advanced Data Structures", "author": "S.Mobit"},
                            {"title": "Basic Data Structures", "author": "S.Mobit"},
                        ],
                    },
                    "phone_numbers": [
                        {"number": "076711110", "type": "Office", "student": 1},
                        {"number": "073008880", "type": "Home", "student": 1},
                    ],
                }
            ],
        )

    def test_list_with_nested_field_without_expanding(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + "?query={name, age, course{name, books}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "course": {
                        "name": "Data Structures",
                        "books": [
                            {"title": "Advanced Data Structures", "author": "S.Mobit"},
                            {"title": "Basic Data Structures", "author": "S.Mobit"},
                        ],
                    },
                }
            ],
        )

    def test_list_with_serializer_field_kwarg(self):
        url = reverse_lazy("course_with_field_kwarg-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_with_serializer_exclude_kwarg(self):
        url = reverse_lazy("course_with_exclude_kwarg-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_with_serializer_return_pk_kwarg(self):
        url = reverse_lazy("course_with_returnpk_kwarg-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [{"name": "Data Structures", "code": "CS210", "books": [1, 2]}],
        )

    def test_list_with_aliased_books(self):
        url = reverse_lazy("course_with_aliased_books-list")
        response = self.client.get(url + "?query={name, tomes{title}}", format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_with_dynamic_serializer_method_field(self):
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        response = self.client.get(url + "?query={name, tomes}", format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                }
            ],
        )

    def test_list_with_expanded_dynamic_serializer_method_field(self):
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        response = self.client.get(url + "?query={name, tomes{title}}", format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_with_dynamic_serializer_method_field_and_aliased_fields(self):
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        response = self.client.get(
            url + "?query={courseName: name, tomes{*, bookTitle: title}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "courseName": "Data Structures",
                    "tomes": [
                        {"bookTitle": "Advanced Data Structures", "author": "S.Mobit"},
                        {"bookTitle": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                }
            ],
        )

    def test_list_with_expanded_dynamic_serializer_method_field_and_aliased_fields(
        self,
    ):
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        response = self.client.get(
            url + "?query={name, tomes{bookTitle: title}}", format="json"
        )

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"bookTitle": "Advanced Data Structures"},
                        {"bookTitle": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_with_dynamic_serializer_method_field_without_query_this_tests_query_and_parsed_query_kwargs_too(
        self,
    ):
        """
        Test that the DynamicSerializerMethodField works without a query present.
        """
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "tomes": [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"},
                        {"title": "Basic Data Structures", "author": "S.Mobit"},
                    ],
                    "related_books": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"},
                    ],
                }
            ],
        )

    def test_list_eager_loading_view_mixin(self):
        """
        Ensure that we apply our prefetching or joins when we explicitly ask for fields in the
        mapping.
        """
        non_mixin_url = reverse_lazy("student-list")
        mixin_url = reverse_lazy("student_eager_loading-list")

        self.add_second_student()

        # This fetches both course names and books for each, so 5 queries total.
        with self.assertNumQueries(5):
            response = self.client.get(
                non_mixin_url + "?query={name, age, course{name, books}}", format="json"
            )
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "course": {
                            "name": "Data Structures",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "course": {
                            "name": "Algorithms",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                    },
                ],
            )

        # This fetches the course information with the student and prefetches once for the books.
        with self.assertNumQueries(2):
            response = self.client.get(
                mixin_url + "?query={name, age, program{name, books}}", format="json"
            )
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                    },
                ],
            )

    def test_list_eager_loading_view_mixin_with_aliased_fields(self):
        """
        Ensure that we apply our prefetching or joins when we explicitly ask for fields in the
        mapping.
        """
        url = reverse_lazy("student_eager_loading-list")

        self.add_second_student()

        # This fetches the course information with the student and prefetches once for the books.
        with self.assertNumQueries(2):
            response = self.client.get(
                url + "?query={name, age, prog: program{name, readings: books}}",
                format="json",
            )
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "prog": {
                            "name": "Data Structures",
                            "readings": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "prog": {
                            "name": "Algorithms",
                            "readings": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                    },
                ],
            )

    def test_list_eager_loading_view_mixin_ignored(self):
        """
        Ensure that we do not apply our joining/prefetching if the mapped fields aren't present.
        """
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        # Make sure that no additional prefetching or select_related are run if we don't ask for
        # nested values.
        with self.assertNumQueries(1):
            response = self.client.get(url + "?query={name, age}", format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                    },
                ],
            )

    def test_list_eager_loading_view_mixin_implicit(self):
        """
        Test that we implicitly apply our nested prefetching, since the field is present.
        """
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        # This would be 5 without doing a select_related and prefetch_related.
        with self.assertNumQueries(2):
            response = self.client.get(
                url + "?query={name, age, program}", format="json"
            )
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                    },
                ],
            )

    def test_list_eager_loading_view_mixin_all_exclude(self):
        """
        Test that we implicitly apply our prefetching with * and exclusion.
        """
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        # This would be 5 without doing a select_related and prefetch_related.
        with self.assertNumQueries(2):
            response = self.client.get(
                url + "?query={*, -phone_numbers, program{*, books{title}}}",
                format="json",
            )
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {"title": "Advanced Data Structures"},
                                {"title": "Basic Data Structures"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design"},
                                {"title": "Proving Algorithms"},
                            ],
                        },
                    },
                ],
            )

    def test_list_eager_loading_mixin_without_query_param(self):
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        with self.assertNumQueries(3):
            response = self.client.get(url, format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                        "phone_numbers": [
                            {"number": "076711110", "type": "Office", "student": 1},
                            {"number": "073008880", "type": "Home", "student": 1},
                        ],
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                        "phone_numbers": [
                            {"number": "075711110", "type": "Office", "student": 2},
                            {"number": "073008880", "type": "Home", "student": 2},
                        ],
                    },
                ],
            )

    def test_list_eager_loading_mixin_with_exclude_operator_but_without_wildcard(self):
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        with self.assertNumQueries(2):
            response = self.client.get(url + "?query={-phone_numbers}", format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                    },
                ],
            )

    def test_list_eager_loading_mixin_with_empty_query_param(self):
        url = reverse_lazy("student_eager_loading-list")
        self.add_second_student()

        with self.assertNumQueries(1):
            response = self.client.get(url + "?query={}", format="json")

            self.assertEqual(
                response.data,
                [
                    {},
                    {},
                ],
            )

    def test_list_eager_loading_mixin_with_prefetch_object_outside_of_list(self):
        """
        Test that a Prefetch object can be provided in the mapping outside of a list.
        """
        url = reverse_lazy("student_eager_loading_prefetch-list")
        self.add_second_student()

        with self.assertNumQueries(2):
            response = self.client.get(url + "?query={program}", format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        }
                    },
                    {
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        }
                    },
                ],
            )

    def test_list_eager_loading_mixin_with_prefetch_object_in_list(self):
        """
        Test that a Prefetch object can be provided in the mapping inside of a list.s
        """
        url = reverse_lazy("student_eager_loading_prefetch-list")
        self.add_second_student()

        with self.assertNumQueries(2):
            response = self.client.get(url + "?query={phone_numbers}", format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "phone_numbers": [
                            {"number": "076711110", "type": "Office", "student": 1},
                            {"number": "073008880", "type": "Home", "student": 1},
                        ]
                    },
                    {
                        "phone_numbers": [
                            {"number": "075711110", "type": "Office", "student": 2},
                            {"number": "073008880", "type": "Home", "student": 2},
                        ]
                    },
                ],
            )

    def test_list_with_auto_apply_eager_loading_set_false(self):
        """
        Test that a Prefetch object can be provided in the mapping inside of a list.s
        """
        url = reverse_lazy("student_auto_apply_eager_loading-list")
        self.add_second_student()

        with self.assertNumQueries(7):
            response = self.client.get(url, format="json")
            self.assertEqual(
                response.data,
                [
                    {
                        "name": "Yezy",
                        "age": 24,
                        "program": {
                            "name": "Data Structures",
                            "code": "CS210",
                            "books": [
                                {
                                    "title": "Advanced Data Structures",
                                    "author": "S.Mobit",
                                },
                                {"title": "Basic Data Structures", "author": "S.Mobit"},
                            ],
                        },
                        "phone_numbers": [
                            {"number": "076711110", "type": "Office", "student": 1},
                            {"number": "073008880", "type": "Home", "student": 1},
                        ],
                    },
                    {
                        "name": "Tyler",
                        "age": 25,
                        "program": {
                            "name": "Algorithms",
                            "code": "CS260",
                            "books": [
                                {"title": "Algorithm Design", "author": "S.Mobit"},
                                {"title": "Proving Algorithms", "author": "S.Mobit"},
                            ],
                        },
                        "phone_numbers": [
                            {"number": "075711110", "type": "Office", "student": 2},
                            {"number": "073008880", "type": "Home", "student": 2},
                        ],
                    },
                ],
            )

    def test_list_on_arguments_with_no_quoted_values(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + '?query=(name: "Yezy", age: 20){name, age, course{name}}',
            format="json",
        )

        self.assertEqual(response.data, [])

    def test_list_on_arguments_with_single_quoted_string_as_value(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + "?query=(name: 'Yezy', age: '20',){name, age, course{name,},}",
            format="json",
        )

        self.assertEqual(response.data, [])

    def test_list_on_arguments_with_double_quoted_string_as_value(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + '?query=(name: "Yezy", age: 20){name, age, course{name}}',
            format="json",
        )

        self.assertEqual(response.data, [])

    def test_list_with_nested_arguments(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + '?query={name, age, course(code: "CS50"){name}}', format="json"
        )

        self.assertEqual(response.data, [])

    def test_list_with_applied_filter_on_nested_aliased_field(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url + '?query={name, age, programme: course(code: "CS015"){code}}',
            format="json",
        )

        self.assertEqual(response.data, [])

    def test_list_with_applied_filter_on_very_deeply_nested_aliased_field(self):
        url = reverse_lazy("student-list")
        response = self.client.get(
            url
            + '?query={name, age, program: course{readings: books(author: "Y.Mobit"){author}}}',
            format="json",
        )

        self.assertEqual(response.data, [])

    def test_options_on_serializer_with_fields_kwarg(self):
        url = reverse_lazy("course_with_field_kwarg-list")
        response = self.client.options(url, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Course With Fields Kwarg List",
                "description": "",
                "renders": ["application/json", "text/html"],
                "parses": [
                    "application/json",
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                ],
                "actions": {
                    "POST": {
                        "name": {
                            "type": "string",
                            "required": True,
                            "read_only": False,
                            "label": "Name",
                            "max_length": 50,
                        },
                        "code": {
                            "type": "string",
                            "required": True,
                            "read_only": False,
                            "label": "Code",
                            "max_length": 30,
                        },
                        "books": {
                            "type": "field",
                            "required": False,
                            "read_only": True,
                            "label": "Books",
                            "child": {
                                "type": "nested object",
                                "required": False,
                                "read_only": True,
                                "children": {
                                    "title": {
                                        "type": "string",
                                        "required": True,
                                        "read_only": False,
                                        "label": "Title",
                                        "max_length": 50,
                                    }
                                },
                            },
                        },
                    }
                },
            },
        )

    def test_options_on_serializer_with_exclude_kwarg(self):
        url = reverse_lazy("course_with_exclude_kwarg-list")
        response = self.client.options(url, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Course With Exclude Kwarg List",
                "description": "",
                "renders": ["application/json", "text/html"],
                "parses": [
                    "application/json",
                    "application/x-www-form-urlencoded",
                    "multipart/form-data",
                ],
                "actions": {
                    "POST": {
                        "name": {
                            "type": "string",
                            "required": True,
                            "read_only": False,
                            "label": "Name",
                            "max_length": 50,
                        },
                        "code": {
                            "type": "string",
                            "required": True,
                            "read_only": False,
                            "label": "Code",
                            "max_length": 30,
                        },
                        "books": {
                            "type": "field",
                            "required": False,
                            "read_only": True,
                            "label": "Books",
                            "child": {
                                "type": "nested object",
                                "required": False,
                                "read_only": True,
                                "children": {
                                    "title": {
                                        "type": "string",
                                        "required": True,
                                        "read_only": False,
                                        "label": "Title",
                                        "max_length": 50,
                                    }
                                },
                            },
                        },
                    }
                },
            },
        )


class DataMutationTests(APITestCase):
    def setUp(self):
        self.book1 = Book.objects.create(
            title="Advanced Data Structures", author="S.Mobit"
        )
        self.book2 = Book.objects.create(
            title="Basic Data Structures", author="S.Mobit"
        )

        self.instructor = Instructor.objects.create(name="Glady")

        self.course1 = Course.objects.create(name="Data Structures", code="CS210")
        self.course2 = Course.objects.create(name="Programming", code="CS150")

        self.course1.books.set([self.book1, self.book2])
        self.course2.books.set([self.book1])

        self.student = Student.objects.create(name="Yezy", age=24, course=self.course1)

        self.phone1 = Phone.objects.create(
            number="076711110", type="Office", student=self.student
        )
        self.phone2 = Phone.objects.create(
            number="073008880", type="Home", student=self.student
        )

    def tearDown(self):
        Book.objects.all().delete()
        Course.objects.all().delete()
        Student.objects.all().delete()

    # **************** Requestless Tests ********************* #

    def test_creating_data_without_request(self):
        serializer = WritableCourseSerializer(
            data={"name": "Data Structures", "code": "CS110", "books": {"add": [1, 2]}},
            query="{name, code, books{title}}",
        )

        serializer.is_valid()
        serializer.save()

        self.assertEqual(
            serializer.data,
            {
                "name": "Data Structures",
                "code": "CS110",
                "books": [
                    {"title": "Advanced Data Structures"},
                    {"title": "Basic Data Structures"},
                ],
            },
        )

    def test_updating_data_without_request(self):
        serializer = WritableStudentSerializer(
            self.student,
            data={
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": {"remove": [1]},
                },
            },
            query="{name, age, course{name, books}, phone_numbers}",
        )

        serializer.is_valid()
        serializer.save()

        self.assertEqual(
            serializer.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "books": [
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    # **************** POST Tests ********************* #

    def test_post_on_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-list")
        data = {"name": "yezy", "age": 33, "course": 2}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    def test_post_on_pk_writable_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Electronics", "code": "E320"},
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Electronics",
                    "code": "E320",
                    "books": [],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    def test_post_on_pk_nested_foreignkey_related_field_with_alias(self):
        url = reverse_lazy("rstudent_with_alias-list")
        data = {"full_name": "yezy", "age": 33, "program": 2}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "full_name": "yezy",
                "age": 33,
                "program": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "contacts": [],
            },
        )

    def test_post_on_pk_nested_nullable_foreignkey_related_field_with_null_not_passed(
        self,
    ):
        url = reverse_lazy("rstudent-list")
        data = {"name": "yezy", "age": 33}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {"name": "yezy", "age": 33, "course": None, "phone_numbers": []},
        )

    def test_post_on_pk_nested_nullable_foreignkey_related_field_with_null_passed(self):
        url = reverse_lazy("rstudent-list")
        data = {"name": "yezy", "age": 33, "course": None}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {"name": "yezy", "age": 33, "course": None, "phone_numbers": []},
        )

    def test_post_on_writable_nested_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    def test_post_on_writable_nested_foreignkey_related_field_with_aliased_fields(self):
        url = reverse_lazy("wstudent_with_alias-list")
        data = {
            "name": "yezy",
            "age": 27,
            "program": {"name": "Programming", "code": "CS50"},
            "contacts": {"add": [1]},
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 27,
                "program": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": None,
                },
                "contacts": [{"number": "076711110", "type": "Office", "student": 2}],
                "study_partner": None,
                "sport_mates": [],
            },
        )

    def test_post_on_writable_nested_nullable_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-list")
        data = {"name": "yezy", "age": 33, "course": None}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {"name": "yezy", "age": 33, "course": None, "phone_numbers": []},
        )

    def test_post_with_add_operation(self):
        url = reverse_lazy("wcourse-list")
        data = {"name": "Data Structures", "code": "CS310", "books": {"add": [1, 2]}}
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {
                        "title": "Basic Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                ],
                "instructor": None,
            },
        )

    def test_post_with_create_operation(self):
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "create": [
                    {"title": "Linear Math", "author": "Me"},
                    {"title": "Algebra Three", "author": "Me"},
                ]
            },
        }
        url = reverse_lazy("wcourse-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "Linear Math", "author": "Me", "genres": []},
                    {"title": "Algebra Three", "author": "Me", "genres": []},
                ],
                "instructor": None,
            },
        )

    def test_post_with_nesting_under_create_operation(self):
        data = {
            "name": "Data Structures",
            "code": "CS315",
            "books": {
                "create": [
                    {
                        "title": "Linear Math 2",
                        "author": "B.Chris",
                        "genres": {
                            "create": [
                                {"title": "Science", "description": "All about nature"}
                            ]
                        },
                    },
                ]
            },
        }
        url = reverse_lazy("wcourse-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS315",
                "books": [
                    {
                        "title": "Linear Math 2",
                        "author": "B.Chris",
                        "genres": [
                            {"title": "Science", "description": "All about nature"}
                        ],
                    },
                ],
                "instructor": None,
            },
        )

    def test_post_with_add_and_create_operations(self):
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "add": [1],
                "create": [{"title": "Algebra Three", "author": "Me"}],
            },
        }
        url = reverse_lazy("wcourse-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {"title": "Algebra Three", "author": "Me", "genres": []},
                ],
                "instructor": None,
            },
        )

    def test_post_on_deep_nested_fields(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {
                "name": "Programming",
                "code": "CS50",
                "books": {
                    "create": [
                        {
                            "title": "Python Tricks",
                            "author": "Dan Bader",
                            "genres": {
                                "create": [
                                    {
                                        "title": "Computing",
                                        "description": "Computer science",
                                    }
                                ]
                            },
                        }
                    ]
                },
            },
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Python Tricks",
                            "author": "Dan Bader",
                            "genres": [
                                {
                                    "title": "Computing",
                                    "description": "Computer science",
                                }
                            ],
                        }
                    ],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    def test_post_on_many_2_one_relation(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
            "phone_numbers": {"create": [{"number": "076750000", "type": "office"}]},
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076750000", "type": "office", "student": 2}
                ],
            },
        )

    def test_post_with_pk_field_inside_writable_nested_field(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "Gray",
            "age": 28,
            "course": {
                "name": "Programming",
                "code": "CS50",
                "instructor": self.instructor.id,
            },
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Gray",
                "age": 28,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": {"name": "Glady"},
                },
                "phone_numbers": [],
            },
        )

    # **************** POST with generic relations ********************* #
    def test_post_on_generic_relation_field(self):
        existing_attachment = Attachment.objects.create(
            content="Existing attachment", document=Post.objects.create()
        )

        response = self.client.post(
            reverse_lazy("post-list"),
            {
                "title": "New post",
                "content": "This is the post",
                "attachments": {
                    "create": [
                        {"content": "This is first attachment"},
                        {"content": "This is second attachment"},
                    ],
                    "add": [existing_attachment.pk],
                },
            },
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 2)
        post = Post.objects.get(title="New post")
        self.assertEqual(Attachment.objects.filter(post=post).count(), 3)
        attachment = Attachment.objects.last()
        self.assertEqual(attachment.content, "This is second attachment")
        existing_attachment.refresh_from_db()
        self.assertEqual(existing_attachment.document, post)

    def test_post_without_attachments(self):
        response = self.client.post(
            reverse_lazy("post-list"),
            data={"title": "Olympic games", "content": "Test post without attachments"},
            format="json",
        )
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Post.objects.count(), 1)
        self.assertEqual(Post.objects.first().attachments.count(), 0)

    # **************** PUT Tests ********************* #

    def test_put_on_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {"name": "yezy", "age": 33, "course": 2}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_on_pk_nested_foreignkey_related_field_with_alias(self):
        url = reverse_lazy("rstudent_with_alias-detail", args=[self.student.id])
        data = {"full_name": "yezy", "age": 33, "program": 2}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "full_name": "yezy",
                "age": 33,
                "program": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_on_writable_nested_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_on_writable_nested_foreignkey_related_field_with_aliased_fields(self):
        url = reverse_lazy("wstudent_with_alias-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 27,
            "program": {"name": "Programming & Data Analysis", "code": "CS55"},
            "contacts": {},
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 27,
                "program": {
                    "name": "Programming & Data Analysis",
                    "code": "CS55",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
                "study_partner": None,
                "sport_mates": [],
            },
        )

    def test_put_on_writable_nested_nullable_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {"name": "yezy", "age": 33}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_on_writable_nested_nullable_foreignkey_related_field_with_empty_string(
        self,
    ):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {"name": "yezy", "age": 33, "course": None}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": None,
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_with_add_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {"name": "Data Structures", "code": "CS410", "books": {"add": [2]}}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {
                        "title": "Basic Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                ],
                "instructor": None,
            },
        )

    def test_put_with_remove_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {"name": "Data Structures", "code": "CS410", "books": {"remove": [1]}}
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": [],
                "instructor": None,
            },
        )

    def test_put_with_create_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "create": [{"title": "Primitive Data Types", "author": "S.Mobit"}]
            },
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {
                        "title": "Primitive Data Types",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                ],
                "instructor": None,
            },
        )

    def test_put_with_update_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "update": {1: {"title": "React Programming", "author": "M.Json"}}
            },
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "React Programming", "author": "M.Json", "genres": []}
                ],
                "instructor": None,
            },
        )

    def test_put_with_update_operation_missing_one_required_nested_field(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "update": {
                    1: {"title": "React Programming"}  # We've removed author field
                }
            },
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "React Programming", "author": "S.Mobit", "genres": []}
                ],
                "instructor": None,
            },
        )

    def test_put_on_deep_nested_fields(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50", "books": {"remove": [1]}},
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_put_on_many_2_one_relation(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
            "phone_numbers": {
                "update": {1: {"number": "073008811", "type": "office"}},
                "create": [{"number": "076750000", "type": "office"}],
            },
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "073008811", "type": "office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                    {"number": "076750000", "type": "office", "student": 1},
                ],
            },
        )

    def test_put_with__all__as_remove_operation_value(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "Davinci",
            "age": 23,
            "course": {
                "name": "Programming",
                "code": "CS50",
                "books": {"remove": "__all__"},
            },
            "phone_numbers": {"remove": "__all__"},
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Davinci",
                "age": 23,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    # **************** PATCH Tests ********************* #

    def test_patch_on_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {"course": 2}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_without_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {
            "age": 35,
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 35,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_pk_nested_foreignkey_related_field_with_alias(self):
        url = reverse_lazy("rstudent_with_alias-detail", args=[self.student.id])
        data = {"age": 33, "program": 2}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "full_name": "Yezy",
                "age": 33,
                "program": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_pk_nested_nullable_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {"age": 30}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 30,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_writable_nested_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {"name": "Yezy Ilomo", "course": {"name": "Programming", "code": "CS50"}}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy Ilomo",
                "age": 24,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_writable_nested_foreignkey_related_field_with_aliased_fields(
        self,
    ):
        url = reverse_lazy("wstudent_with_alias-detail", args=[self.student.id])
        data = {
            "age": 28,
            "program": {"name": "Programming & Data Analysis", "code": "CS55"},
            "contacts": {},
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 28,
                "program": {
                    "name": "Programming & Data Analysis",
                    "code": "CS55",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
                "study_partner": None,
                "sport_mates": [],
            },
        )

    def test_patch_on_writable_nested_nullable_foreignkey_related_field_without_null_value(
        self,
    ):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 26,
            # "course": None  # We are not passing null
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 26,
                "course": {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_writable_nested_nullable_foreignkey_related_field_with_null_value(
        self,
    ):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {"name": "yezy", "age": 33, "course": None}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": None,
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_with_add_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {"name": "Data Structures", "code": "CS410", "books": {"add": [2]}}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {
                        "title": "Basic Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                ],
                "instructor": None,
            },
        )

    def test_patch_with_remove_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {"name": "Data Structures", "code": "CS410", "books": {"remove": [1]}}
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": [],
                "instructor": None,
            },
        )

    def test_patch_with_create_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "create": [{"title": "Primitive Data Types", "author": "S.Mobit"}]
            },
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {
                        "title": "Advanced Data Structures",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                    {
                        "title": "Primitive Data Types",
                        "author": "S.Mobit",
                        "genres": [],
                    },
                ],
                "instructor": None,
            },
        )

    def test_patch_with_update_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "update": {1: {"title": "React Programming", "author": "M.Json"}}
            },
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "React Programming", "author": "M.Json", "genres": []}
                ],
                "instructor": None,
            },
        )

    def test_patch_with_update_operation_missing_one_required_nested_field(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
            "name": "Data Structures",
            "code": "CS310",
            "books": {
                "update": {
                    1: {"title": "React Programming"}  # We've removed author field
                }
            },
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "React Programming", "author": "S.Mobit", "genres": []}
                ],
                "instructor": None,
            },
        )

    def test_patch_with_mixed_operations(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {
                "name": "Programming",
                "code": "CS50",
                "books": {
                    "update": {
                        1: {
                            "title": "React Programming",
                            "author": "K.Kennedy",
                            "genres": {
                                # update_operations applies here since the parent is "update"
                                "remove": [],
                                "add": [],
                                "create": [
                                    {
                                        "title": "Modern Programming",
                                        "description": "New tools",
                                    }
                                ],
                                "update": {},
                            },
                        }
                    },
                    "create": [
                        {
                            "title": "CS Foundation",
                            "author": "T.Howard",
                            "genres": {
                                # create_operations applies here since the parent is "create"
                                "add": [],
                                "create": [
                                    {
                                        "title": "Classical Programming",
                                        "description": "Classical tech tools",
                                    }
                                ],
                            },
                        }
                    ],
                },
            },
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "React Programming",
                            "author": "K.Kennedy",
                            "genres": [
                                {
                                    "title": "Modern Programming",
                                    "description": "New tools",
                                }
                            ],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "CS Foundation",
                            "author": "T.Howard",
                            "genres": [
                                {
                                    "title": "Classical Programming",
                                    "description": "Classical tech tools",
                                }
                            ],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
            },
        )

    def test_patch_on_many_2_one_relation(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
            "phone_numbers": {
                "update": {1: {"number": "073008811", "type": "office"}},
                "create": [{"number": "076750000", "type": "office"}],
            },
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "phone_numbers": [
                    {"number": "073008811", "type": "office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                    {"number": "076750000", "type": "office", "student": 1},
                ],
            },
        )

    def test_patch_with__all__as_remove_operation_value(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "Davinci",
            "age": 33,
            "course": {
                "name": "Programming",
                "code": "CS50",
                "books": {"remove": "__all__"},
            },
            "phone_numbers": {"remove": "__all__"},
        }
        response = self.client.patch(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Davinci",
                "age": 33,
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [],
                    "instructor": None,
                },
                "phone_numbers": [],
            },
        )

    def test_patch_with_mixed_operations_on_generic_relation(self):
        post = Post.objects.create()
        attachment = Attachment.objects.create(document=post)
        removed_attachment = Attachment.objects.create(document=post, content="removed")
        attachment_to_add = Attachment.objects.create(
            content="attachment to add",
            document=Post.objects.create(title="Another post"),
        )

        response = self.client.patch(
            reverse_lazy("post-detail", args=[post.pk]),
            {
                "attachments": {
                    "create": [
                        {"content": "new attachment"},
                    ],
                    "update": {str(attachment.pk): {"content": "old attachment"}},
                    "remove": [removed_attachment.pk],
                    "add": [attachment_to_add.pk],
                }
            },
            format="json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Attachment.objects.filter(post=post).count(), 3)
        attachment.refresh_from_db()
        self.assertEqual(attachment.content, "old attachment")
        with self.assertRaises(Attachment.DoesNotExist):
            removed_attachment.refresh_from_db()

        attachment_to_add.refresh_from_db()
        self.assertEqual(attachment_to_add.document, post)
        self.assertEqual(
            Attachment.objects.get(content="new attachment").document, post
        )


class DataQueryingAndMutationTests(APITestCase):
    def setUp(self):
        self.book1 = Book.objects.create(
            title="Advanced Data Structures", author="S.Mobit"
        )
        self.book2 = Book.objects.create(
            title="Basic Data Structures", author="S.Mobit"
        )

        self.course1 = Course.objects.create(name="Data Structures", code="CS210")
        self.course2 = Course.objects.create(name="Programming", code="CS150")

        self.course1.books.set([self.book1, self.book2])
        self.course2.books.set([self.book1])

        self.student = Student.objects.create(name="Yezy", age=24, course=self.course1)

        self.phone1 = Phone.objects.create(
            number="076711110", type="Office", student=self.student
        )
        self.phone2 = Phone.objects.create(
            number="073008880", type="Home", student=self.student
        )

    def tearDown(self):
        Book.objects.all().delete()
        Course.objects.all().delete()
        Student.objects.all().delete()

    # **************** POST Tests ********************* #

    def test_post_on_pk_nested_foreignkey_related_field_mix_with_query_param(self):
        url = reverse_lazy("rstudent-list")
        data = {"name": "yezy", "age": 33, "course": 2}
        response = self.client.post(url + "?query={course}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                }
            },
        )

    def test_post_on_pk_nested_foreignkey_related_field_with_alias_mix_with_query_param(
        self,
    ):
        url = reverse_lazy("rstudent_with_alias-list")
        data = {"full_name": "yezy", "age": 33, "program": 2}
        response = self.client.post(
            url + "?query={full_name, program}", data, format="json"
        )

        self.assertEqual(
            response.data,
            {
                "full_name": "yezy",
                "program": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
            },
        )

    def test_post_on_writable_nested_foreignkey_related_field_mix_with_query_param(
        self,
    ):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
        }
        response = self.client.post(
            url + "?query={course{name, books{}}}", data, format="json"
        )

        self.assertEqual(
            response.data, {"course": {"name": "Programming", "books": []}}
        )

    def test_post_with_add_operation_mix_with_query_param(self):
        url = reverse_lazy("wcourse-list")
        data = {"name": "Data Structures", "code": "CS310", "books": {"add": [1, 2]}}
        response = self.client.post(url + "?query={books{title}}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "books": [
                    {"title": "Advanced Data Structures"},
                    {"title": "Basic Data Structures"},
                ]
            },
        )

    def test_post_with_add_operation_mix_with_query_param_and_alias_fields(self):
        url = reverse_lazy("wcourse-list")
        data = {"name": "Data Structures", "code": "CS310", "books": {"add": [1, 2]}}
        response = self.client.post(
            url + "?query={books{bookTitle: title}}", data, format="json"
        )

        self.assertEqual(
            response.data,
            {
                "books": [
                    {"bookTitle": "Advanced Data Structures"},
                    {"bookTitle": "Basic Data Structures"},
                ]
            },
        )

    def test_post_on_self_referencing_nested_field(self):
        url = reverse_lazy("wstudent_with_alias-list")
        data = {
            "name": "Gwen",
            "age": 27,
            "program": {"name": "Programming & Data Analysis", "code": "CS010"},
            "contacts": {},
            "study_partner": {"name": "Ilomo", "age": 24},
            "sport_mates": {
                "add": [1],
                "create": [{"name": "Yoram", "age": 26}, {"name": "Gaby", "age": 23}],
            },
        }
        response = self.client.post(
            url + "?query={*, study_partner{name}, sport_mates{name, age}}",
            data,
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "Gwen",
                "age": 27,
                "program": {
                    "name": "Programming & Data Analysis",
                    "code": "CS010",
                    "books": [],
                    "instructor": None,
                },
                "contacts": [],
                "study_partner": {"name": "Ilomo"},
                "sport_mates": [
                    {"name": "Yezy", "age": 24},
                    {"name": "Yoram", "age": 26},
                    {"name": "Gaby", "age": 23},
                ],
            },
        )

    # **************** PUT Tests ********************* #

    def test_put_on_pk_nested_foreignkey_related_field_mix_with_query_param(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {"name": "Yezy", "age": 25, "course": 2}
        response = self.client.put(url + "?query={course}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                }
            },
        )

    def test_put_on_writable_nested_foreignkey_related_field_mix_with_query_param(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "Yezy",
            "age": 25,
            "course": {"name": "Programming", "code": "CS50"},
        }
        response = self.client.put(url + "?query={name, course}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
            },
        )

    def test_put_on_deep_nested_fields_mix_with_query_param(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50", "books": {"remove": [1]}},
        }
        response = self.client.put(
            url + "?query={course{books{title}}}", data, format="json"
        )

        self.assertEqual(
            response.data, {"course": {"books": [{"title": "Basic Data Structures"}]}}
        )

    def test_put_on_deep_nested_fields_mix_with_query_param_and_aliased_fields(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50", "books": {"remove": [1]}},
        }
        response = self.client.put(
            url + "?query={programme: course{readings: books{bookTitle: title}}}",
            data,
            format="json",
        )

        self.assertEqual(
            response.data,
            {"programme": {"readings": [{"bookTitle": "Basic Data Structures"}]}},
        )

    def test_put_on_self_referencing_nested_field(self):
        url = reverse_lazy("wstudent_with_alias-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 27,
            "program": {"name": "Programming & Data Analysis", "code": "CS55"},
            "contacts": {},
            "study_partner": {"name": "Ilomo", "age": 24},
            "sport_mates": {
                "create": [{"name": "Yoram", "age": 26}, {"name": "Gaby", "age": 23}]
            },
        }
        response = self.client.put(
            url + "?query={*, study_partner{name}, sport_mates{name, age}}",
            data,
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 27,
                "program": {
                    "name": "Programming & Data Analysis",
                    "code": "CS55",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
                "study_partner": {"name": "Ilomo"},
                "sport_mates": [
                    {"name": "Yoram", "age": 26},
                    {"name": "Gaby", "age": 23},
                ],
            },
        )

    # **************** PATCH Tests ********************* #

    def test_patch_on_pk_nested_foreignkey_related_field_mix_with_query_param(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {"course": 2}
        response = self.client.patch(url + "?query={name, course}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "course": {
                    "name": "Programming",
                    "code": "CS150",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        }
                    ],
                    "instructor": None,
                },
            },
        )

    def test_patch_on_writable_nested_foreignkey_related_field_mix_with_query_param(
        self,
    ):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {"name": "Yezy Ilomo", "course": {"name": "Programming", "code": "CS50"}}
        response = self.client.patch(url + "?query={name, course}", data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy Ilomo",
                "course": {
                    "name": "Programming",
                    "code": "CS50",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
            },
        )

    def test_patch_on_deep_nested_fields_mix_with_query_param(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50", "books": {"remove": [1]}},
        }
        response = self.client.patch(
            url + "?query={course{books{title}}}", data, format="json"
        )

        self.assertEqual(
            response.data, {"course": {"books": [{"title": "Basic Data Structures"}]}}
        )

    def test_patch_on_deep_nested_fields_mix_with_query_param_and_aliased_fields(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50", "books": {"remove": [1]}},
        }
        response = self.client.patch(
            url + "?query={programme: course{books{name: title}}}", data, format="json"
        )

        self.assertEqual(
            response.data, {"programme": {"books": [{"name": "Basic Data Structures"}]}}
        )

    def test_patch_on_self_referencing_nested_field(self):
        url = reverse_lazy("wstudent_with_alias-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 27,
            "program": {"name": "Programming & Data Analysis", "code": "CS55"},
            "contacts": {},
            "study_partner": 1,
            "sport_mates": {
                "create": [{"name": "Yoram", "age": 26}, {"name": "Gaby", "age": 23}]
            },
        }
        response = self.client.patch(
            url + "?query={*, study_partner{name}, sport_mates{name, age}}",
            data,
            format="json",
        )

        self.assertEqual(
            response.data,
            {
                "name": "yezy",
                "age": 27,
                "program": {
                    "name": "Programming & Data Analysis",
                    "code": "CS55",
                    "books": [
                        {
                            "title": "Advanced Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                        {
                            "title": "Basic Data Structures",
                            "author": "S.Mobit",
                            "genres": [],
                        },
                    ],
                    "instructor": None,
                },
                "contacts": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1},
                ],
                "study_partner": {"name": "Yezy"},
                "sport_mates": [
                    {"name": "Yoram", "age": 26},
                    {"name": "Gaby", "age": 23},
                ],
            },
        )
