from django.urls import reverse
from rest_framework.test import APITestCase
from tests.testapp.models import Book, Course, Student, Phone


class ViewTests(APITestCase):
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
        url = reverse("book-detail", args=[self.book1.id])
        response = self.client.get(url + '?query={title, author}', format="json")

        self.assertEqual(
            response.data,
            {
                "title": "Advanced Data Structures",
                "author": "S.Mobit"
            },
        )

    def test_retrieve_with_nested_flat_query(self):
        url = reverse("student-detail", args=[self.student.id])
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
        url = reverse("course-detail", args=[self.course.id])
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
        url = reverse("student-detail", args=[self.student.id])
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

    def test_retrieve_without_query_param(self):
        url = reverse("student-detail", args=[self.student.id])
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
                    {"number": "076711110", "type": "Office"},
                    {"number": "073008880", "type": "Home"}
                ]
            }
        )


    # *************** list tests **************

    def test_list_with_flat_query(self):
        url = reverse("book-list")
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
        url = reverse("student-list")
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
        url = reverse("course-list")
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
        url = reverse("student-list")
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
        url = reverse("student-list")
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
                            {"title": "Basic Data Structures",}
                        ]
                    }
                }
            ]
        )

    def test_list_without_query_param(self):
        url = reverse("student-list")
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
                        {"number": "076711110", "type": "Office"},
                        {"number": "073008880", "type": "Home"}
                    ]
                }
            ]
        )