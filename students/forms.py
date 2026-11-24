from django import forms

from .models import Student


class StudentForm(forms.ModelForm):
    age = forms.IntegerField(min_value=1, max_value=120)

    class Meta:
        model = Student
        fields = ["name", "email", "age", "course", "phone"]
        widgets = {
            "name": forms.TextInput(attrs={"placeholder": "e.g. Ana Reyes"}),
            "email": forms.EmailInput(attrs={"placeholder": "student@example.com"}),
            "age": forms.NumberInput(attrs={"min": 1, "max": 120, "placeholder": "21"}),
            "course": forms.TextInput(attrs={"placeholder": "Full-Stack"}),
            "phone": forms.TelInput(attrs={"placeholder": "090-1234-5678"}),
        }
