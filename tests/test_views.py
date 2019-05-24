from django.urls import reverse
from rest_framework.test import APITestCase
from tests.testapp.models import Book, Course, Student


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
