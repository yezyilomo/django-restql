from django.db import models


class Genre(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.CharField(max_length=50)
    genre = models.ForeignKey(Genre, blank=True, null=True, on_delete=models.CASCADE, related_name="books")


class Course(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30)
    books = models.ManyToManyField(Book, blank=True, related_name="courses")


class Student(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    course = models.ForeignKey(Course, blank=True, null=True, on_delete=models.CASCADE, related_name="students")


class Phone(models.Model):
    number = models.CharField(max_length=15)
    type = models.CharField(max_length=50)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="phone_numbers")
