from django.contrib import admin

from .models import Student


@admin.register(Student)
class StudentAdmin(admin.ModelAdmin):
    list_display = ("name", "email", "age", "course", "enrolled_date")
    search_fields = ("name", "email", "course")
