from django.test import TestCase
from django.urls import reverse

from .models import Student


class StudentManagementTests(TestCase):
    def setUp(self):
        self.student = Student.objects.create(
            name="Juan Dela Cruz",
            email="juan@example.com",
            age=21,
            course="Full-Stack",
        )

    def test_student_list_shows_records_and_summary(self):
        response = self.client.get(reverse("students:list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.student.name)
        self.assertContains(response, "Total students")

    def test_create_student_persists_optional_phone(self):
        response = self.client.post(reverse("students:create"), {
            "name": "Ana Reyes",
            "email": "ana@example.com",
            "age": 23,
            "course": "Backend",
            "phone": "090-1111-2222",
        })

        self.assertRedirects(response, reverse("students:list"))
        student = Student.objects.get(email="ana@example.com")
        self.assertEqual(student.phone, "090-1111-2222")

    def test_duplicate_email_is_rejected(self):
        response = self.client.post(reverse("students:create"), {
            "name": "Another Juan",
            "email": self.student.email,
            "age": 20,
            "course": "Backend",
            "phone": "",
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "already exists")
        self.assertEqual(Student.objects.count(), 1)

    def test_delete_requires_post_and_removes_student(self):
        url = reverse("students:delete", args=[self.student.pk])

        self.assertEqual(self.client.get(url).status_code, 405)
        response = self.client.post(url)

        self.assertRedirects(response, reverse("students:list"))
        self.assertFalse(Student.objects.filter(pk=self.student.pk).exists())
