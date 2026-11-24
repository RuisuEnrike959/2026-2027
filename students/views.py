from django.contrib import messages
from django.db.models import Avg, Count, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import StudentForm
from .models import Student


def student_list(request):
    query = request.GET.get("q", "").strip()
    students = Student.objects.all().order_by("name", "pk")
    if query:
        students = students.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(course__icontains=query)
            | Q(phone__icontains=query)
        )

    summary = Student.objects.aggregate(total=Count("pk"), average_age=Avg("age"))
    context = {
        "students": students,
        "query": query,
        "total_students": summary["total"],
        "total_courses": Student.objects.values("course").distinct().count(),
        "average_age": round(summary["average_age"]) if summary["average_age"] is not None else None,
    }
    return render(request, "students/student_list.html", context)


def student_create(request):
    if request.method == "POST":
        form = StudentForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Student added successfully.")
            return redirect("students:list")
    else:
        form = StudentForm()
    return render(request, "students/student_form.html", {"form": form, "page_title": "Add student"})


def student_update(request, pk):
    student = get_object_or_404(Student, pk=pk)
    if request.method == "POST":
        form = StudentForm(request.POST, instance=student)
        if form.is_valid():
            form.save()
            messages.success(request, "Student updated successfully.")
            return redirect("students:list")
    else:
        form = StudentForm(instance=student)
    return render(
        request,
        "students/student_form.html",
        {"form": form, "page_title": "Edit student", "student": student},
    )


@require_POST
def student_delete(request, pk):
    student = get_object_or_404(Student, pk=pk)
    student.delete()
    messages.success(request, "Student deleted successfully.")
    return redirect("students:list")
