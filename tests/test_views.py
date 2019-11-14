from django.urls import reverse_lazy
from rest_framework.test import APITestCase
from tests.testapp.models import Book, Course, Student, Phone


class DataQueryingTests(APITestCase):
    def setUp(self):
        self.book1 = Book.objects.create(title="Advanced Data Structures", author="S.Mobit")
        self.book2 = Book.objects.create(title="Basic Data Structures", author="S.Mobit")

        self.course = Course.objects.create(
            name="Data Structures", code="CS210"
        )

        self.course.books.set([self.book1, self.book2])

        self.student = Student.objects.create(
            name="Yezy", age=24, course=self.course
        )

        self.phone1 = Phone.objects.create(number="076711110", type="Office", student=self.student)
        self.phone2 = Phone.objects.create(number="073008880", type="Home", student=self.student)

    def tearDown(self):
        Book.objects.all().delete()
        Course.objects.all().delete()
        Student.objects.all().delete()


    # *************** retrieve tests **************

    def test_retrieve_with_flat_query(self):
        url = reverse_lazy("book-detail", args=[self.book1.id])
        response = self.client.get(url + '?query={title, author}', format="json")

        self.assertEqual(
            response.data,
            {
                "title": "Advanced Data Structures",
                "author": "S.Mobit"
            },
        )

    def test_retrieve_with_nested_flat_query(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(url + '?query={name, age, course{name}}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "course": {
                    "name": "Data Structures"
                }
            }
        )

    def test_retrieve_with_nested_iterable_query(self):
        url = reverse_lazy("course-detail", args=[self.course.id])
        response = self.client.get(url + '?query={name, code, books{title}}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
                "books": [
                    {"title": "Advanced Data Structures"},
                    {"title": "Basic Data Structures"}
                ]
            }
        )

    def test_retrieve_reverse_relation_with_nested_iterable_query(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(url + '?query={name, age, phone_numbers{number}}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "phone_numbers": [
                    {"number": "076711110"},
                    {"number": "073008880"}
                ]
            }
        )

    def test_retrieve_with_exclude_operator_applied_at_the_top_level(self):
        url = reverse_lazy("course-detail", args=[self.course.id])
        response = self.client.get(url + '?query={-books}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS210",
            }
        )


    def test_retrieve_with_exclude_operator_applied_on_a_nested_field(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(url + '?query={name, age, phone_numbers{-number, -student}}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "age": 24,
                "phone_numbers": [
                    {"type": "Office"},
                    {"type": "Home"}
                ]
            }
        )

    def test_retrieve_with_exclude_operator_applied_at_the_top_level_and_expand_a_nested_field(self):
        url = reverse_lazy("student-detail", args=[self.student.id])
        response = self.client.get(url + '?query={-age, -course, phone_numbers{number}}', format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Yezy",
                "phone_numbers": [
                    {"number": "076711110"},
                    {"number": "073008880"}
                ]
            }
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
                        {"title": "Basic Data Structures", "author": "S.Mobit"}
                    ]
                },
                "phone_numbers": [
                    {"number": "076711110", "type": "Office", "student": 1},
                    {"number": "073008880", "type": "Home", "student": 1}
                ]
            }
        )


    # *************** list tests **************

    def test_list_with_flat_query(self):
        url = reverse_lazy("book-list")
        response = self.client.get(url + '?query={title, author}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "title": "Advanced Data Structures",
                    "author": "S.Mobit"
                },
                {
                    "title": "Basic Data Structures",
                    "author": "S.Mobit"
                }
            ]
        )


    def test_list_with_nested_flat_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={name, age, course{name}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "course": {
                        "name": "Data Structures"
                    }
                }
            ]
        )

    def test_list_with_nested_iterable_query(self):
        url = reverse_lazy("course-list")
        response = self.client.get(url + '?query={name, code, books{title}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"}
                    ]
                }
            ]
        )

    def test_list_reverse_relation_with_nested_iterable_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={name, age, phone_numbers{number}}', format="json")
        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "phone_numbers": [
                        {"number": "076711110"},
                        {"number": "073008880"}
                    ]
                }
            ]
        )

    def test_list_with_nested_flat_and_deep_iterable_query(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={name, age, course{name, books{title}}}', format="json")

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
                            {"title": "Basic Data Structures"}
                        ]
                    }
                }
            ]
        )

    def test_list_with_exclude_operator_applied_at_the_top_level(self):
        url = reverse_lazy("course-list")
        response = self.client.get(url + '?query={-books}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                }
            ]
        )


    def test_list_with_exclude_operator_applied_on_a_nested_field(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={name, age, phone_numbers{-number, -student}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "age": 24,
                    "phone_numbers": [
                        {"type": "Office"},
                        {"type": "Home"}
                    ]
                }
            ]
        )

    def test_list_with_exclude_operator_applied_at_the_top_level_and_expand_a_nested_field(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={-age, -course, phone_numbers{number}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Yezy",
                    "phone_numbers": [
                        {"number": "076711110"},
                        {"number": "073008880"}
                    ]
                }
            ]
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
                            {"title": "Basic Data Structures", "author": "S.Mobit"}
                        ]
                    },
                    "phone_numbers": [
                        {"number": "076711110", "type": "Office", "student": 1},
                        {"number": "073008880", "type": "Home", "student": 1}
                    ]
                }
            ]
        )

    def test_list_with_nested_field_without_expanding(self):
        url = reverse_lazy("student-list")
        response = self.client.get(url + '?query={name, age, course{name, books}}', format="json")

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
                            {"title": "Basic Data Structures", "author": "S.Mobit"}
                        ]
                    }
                }
            ]
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
                        {"title": "Basic Data Structures"}
                    ]
                }
            ]
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
                        {"title": "Basic Data Structures"}
                    ]
                }
            ]
        )

    def test_list_with_serializer_return_pk_kwarg(self):
        url = reverse_lazy("course_with_returnpk_kwarg-list")
        response = self.client.get(url, format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "code": "CS210",
                    "books": [1,2]
                }
            ]
        )

    def test_list_with_aliased_books(self):
        url = reverse_lazy("course_with_aliased_books-list")
        
        response = self.client.get(url + '?query={name, tomes{title}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"}
                    ]
                }
            ]
        )

    def test_list_with_dynamic_serializer_method_field(self):
        url = reverse_lazy("course_with_dynamic_serializer_method_field-list")
        
        response = self.client.get(url + '?query={name, tomes{title}}', format="json")

        self.assertEqual(
            response.data,
            [
                {
                    "name": "Data Structures",
                    "tomes": [
                        {"title": "Advanced Data Structures"},
                        {"title": "Basic Data Structures"}
                    ]
                }
            ]
        )


class DataMutationTests(APITestCase):
    def setUp(self):
        self.book1 = Book.objects.create(title="Advanced Data Structures", author="S.Mobit")
        self.book2 = Book.objects.create(title="Basic Data Structures", author="S.Mobit")

        self.course1 = Course.objects.create(
            name="Data Structures", code="CS210"
        )
        self.course2 = Course.objects.create(
            name="Programming", code="CS150"
        )

        self.course1.books.set([self.book1, self.book2])
        self.course2.books.set([self.book1])

        self.student = Student.objects.create(
            name="Yezy", age=24, course=self.course1
        )

        self.phone1 = Phone.objects.create(number="076711110", type="Office", student=self.student)
        self.phone2 = Phone.objects.create(number="073008880", type="Home", student=self.student)

    def tearDown(self):
        Book.objects.all().delete()
        Course.objects.all().delete()
        Student.objects.all().delete()


    # **************** POST Tests ********************* #

    def test_post_on_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": 2
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 
                'age': 33, 
                'course': {
                    'name': 'Programming', 
                    'code': 'CS150', 
                    'books': [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"}
                    ]
                }, 
                'phone_numbers': []
            }
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
                'name': 'yezy', 
                'age': 33, 
                'course': {
                    'name': 'Programming', 
                    'code': 'CS50', 
                    'books': []
                }, 
                'phone_numbers': []
            }
        )

    def test_post_with_add_operation(self):
        url = reverse_lazy("rcourse-list")
        data = {
                "name": "Data Structures",
                "code": "CS310",
                "books": {"add":[1,2]}
        }
        response = self.client.post(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {'title': 'Advanced Data Structures', 'author': 'S.Mobit'},
                    {'title': 'Basic Data Structures', 'author': 'S.Mobit'}
                ]
            }
        )

    def test_post_with_create_operation(self):
        data = {
                "name": "Data Structures",
                "code": "CS310",
                "books": {"create": [
                    {"title": "Linear Math", "author": "Me"},
                    {"title": "Algebra Three", "author": "Me"}
                ]}
        }
        url = reverse_lazy("wcourse-list")
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "Linear Math", "author": "Me"},
                    {"title": "Algebra Three", "author": "Me"}
                ]
            }
        )

    def test_post_on_deep_nested_fields(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {
                "name": "Programming", 
                "code": "CS50",
                "books": {"create": [
                    {"title": "Python Tricks", "author": "Dan Bader"}
                ]}
            }
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 
                'age': 33, 
                'course': {
                    'name': 'Programming', 
                    'code': 'CS50', 
                    'books': [
                        {"title": "Python Tricks", "author": "Dan Bader"}
                    ]
                }, 
                'phone_numbers': []
            }
        )

    def test_post_on_many_2_one_relation(self):
        url = reverse_lazy("wstudent-list")
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
            "phone_numbers": {
                'create': [
                    {'number': '076750000', 'type': 'office'}
                ]
            }
        }
        response = self.client.post(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 
                'age': 33, 
                'course': {
                    'name': 'Programming', 
                    'code': 'CS50', 
                    'books': []
                }, 
                'phone_numbers': [
                    {'number': '076750000', 'type': 'office', 'student': 2}
                ]
            }
        )

    # **************** PUT Tests ********************* #

    def test_put_on_pk_nested_foreignkey_related_field(self):
        url = reverse_lazy("rstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": 2
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 'age': 33, 
                'course': {
                    'name': 'Programming', 'code': 'CS150', 
                    'books': [
                        {"title": "Advanced Data Structures", "author": "S.Mobit"}
                    ]
                }, 
                'phone_numbers': [
                    {'number': '076711110', 'type': 'Office', 'student': 1}, 
                    {'number': '073008880', 'type': 'Home', 'student': 1} 
                ]
            }
        )

    def test_put_on_writable_nested_foreignkey_related_field(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"}
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 'age': 33, 
                'course': {
                    'name': 'Programming', 'code': 'CS50', 
                    'books': [
                        {'title': 'Advanced Data Structures', 'author': 'S.Mobit'},
                        {'title': 'Basic Data Structures', 'author': 'S.Mobit'}
                    ]
                }, 
                'phone_numbers': [
                    {'number': '076711110', 'type': 'Office', 'student': 1}, 
                    {'number': '073008880', 'type': 'Home', 'student': 1}
                    
                ]
            }
        )

    def test_put_with_add_operation(self):
        url = reverse_lazy("rcourse-detail", args=[self.course2.id])
        data = {
                "name": "Data Structures",
                "code": "CS410",
                "books": {
                    "add": [2]
                }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": [
                    {'title': 'Advanced Data Structures', 'author': 'S.Mobit'},
                    {'title': 'Basic Data Structures', 'author': 'S.Mobit'}
                ]
            }
        )

    def test_put_with_remove_operation(self):
        url = reverse_lazy("rcourse-detail", args=[self.course2.id])
        data = {
                "name": "Data Structures",
                "code": "CS410",
                "books": {
                    "remove": [1]
                }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS410",
                "books": []
            }
        )

    def test_put_with_create_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
                "name": "Data Structures",
                "code": "CS310",
                "books": {
                    "create": [
                        {"title": "Primitive Data Types", "author": "S.Mobit"}
                    ]
                }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {'title': 'Advanced Data Structures', 'author': 'S.Mobit'},
                    {"title": "Primitive Data Types", "author": "S.Mobit"}
                ]
            }
        )

    def test_put_with_update_operation(self):
        url = reverse_lazy("wcourse-detail", args=[self.course2.id])
        data = {
                "name": "Data Structures",
                "code": "CS310",
                "books": {
                    "update": {
                        1: {"title": "React Programming", "author": "M.Json"}
                    }
                }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                "name": "Data Structures",
                "code": "CS310",
                "books": [
                    {"title": "React Programming", "author": "M.Json"}
                ]
            }
        )

    def test_put_on_deep_nested_fields(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {
                "name": "Programming", 
                "code": "CS50", 
                "books": {
                    "remove": [1]
                }
            }
        }
        response = self.client.put(url, data, format="json")
        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 'age': 33, 
                'course': {
                    'name': 'Programming', 'code': 'CS50', 
                    'books': [
                        {'title': 'Basic Data Structures', 'author': 'S.Mobit'}
                    ]
                }, 
                'phone_numbers': [
                    {'number': '076711110', 'type': 'Office', 'student': 1}, 
                    {'number': '073008880', 'type': 'Home', 'student': 1}
                ]
            }
        )

    def test_put_on_many_2_one_relation(self):
        url = reverse_lazy("wstudent-detail", args=[self.student.id])
        data = {
            "name": "yezy",
            "age": 33,
            "course": {"name": "Programming", "code": "CS50"},
            "phone_numbers": {
                'update': {
                    1: {'number': '073008811', 'type': 'office'}
                },
                'create': [
                    {'number': '076750000', 'type': 'office'}
                ]
            }
        }
        response = self.client.put(url, data, format="json")

        self.assertEqual(
            response.data,
            {
                'name': 'yezy', 'age': 33, 
                'course': {
                    'name': 'Programming', 'code': 'CS50', 
                    'books': [
                        {'title': 'Advanced Data Structures', 'author': 'S.Mobit'},
                        {'title': 'Basic Data Structures', 'author': 'S.Mobit'}
                    ]
                }, 
                'phone_numbers': [
                    {'number': '073008811', 'type': 'office', 'student': 1}, 
                    {'number': '073008880', 'type': 'Home', 'student': 1},
                    {'number': '076750000', 'type': 'office', 'student': 1}
                    
                ]
            }
        )