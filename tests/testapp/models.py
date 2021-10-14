from django.db import models


class Genre(models.Model):
    title = models.CharField(max_length=50)
    description = models.TextField()


class Book(models.Model):
    title = models.CharField(max_length=50)
    author = models.CharField(max_length=50)
    genres = models.ManyToManyField(Genre, blank=True, related_name="books")


class Instructor(models.Model):
    name = models.CharField(max_length=50)


class Course(models.Model):
    name = models.CharField(max_length=50)
    code = models.CharField(max_length=30)
    books = models.ManyToManyField(Book, blank=True, related_name="courses")
    instructor = models.ForeignKey(Instructor, blank=True, null=True, on_delete=models.CASCADE, related_name="courses")


class Student(models.Model):
    name = models.CharField(max_length=50)
    age = models.IntegerField()
    course = models.ForeignKey(Course, blank=True, null=True, on_delete=models.CASCADE, related_name="students")
    study_partner = models.OneToOneField('self', blank=True, null=True, on_delete=models.CASCADE)
    sport_partners = models.ManyToManyField('self', blank=True, related_name="sport_partners")


class Phone(models.Model):
    number = models.CharField(max_length=15)
    type = models.CharField(max_length=50)
    student = models.ForeignKey(Student, on_delete=models.CASCADE, related_name="phone_numbers")
