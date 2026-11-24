from django.db import models


class Student(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    age = models.PositiveIntegerField()
    course = models.CharField(max_length=100)
    enrolled_date = models.DateField(auto_now_add=True)
    phone = models.CharField(max_length=20, blank=True, default="")

    def __str__(self):
        return self.name
