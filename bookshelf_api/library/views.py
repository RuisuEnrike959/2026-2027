from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.db.models import Avg
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework import viewsets
from rest_framework.filters import SearchFilter

from .filters import NullsLastOrderingFilter
from .forms import ReviewForm
from .models import Author, Book, Review
from .permissions import IsAdminOrReadOnlyApiStaff
from .serializers import AuthorSerializer, BookSerializer, ReviewSerializer


def home(request):
    books = Book.objects.filter(show_on_home=True).select_related("author")
    return render(
        request,
        "library/home.html",
        {
            "books": books,
            "authors": Author.objects.all(),
            "is_catalog": False,
        },
    )


def sign_up(request):
    if request.user.is_authenticated:
        return redirect("home")

    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save(commit=False)
        user.is_staff = False
        user.is_superuser = False
        user.save()
        login(request, user)
        return redirect("home")

    return render(request, "registration/signup.html", {"form": form})


def book_list(request):
    books = Book.objects.select_related("author")
    return render(
        request,
        "library/home.html",
        {"books": books, "is_catalog": True},
    )


def book_detail(request, pk):
    book = get_object_or_404(
        Book.objects.select_related("author")
        .prefetch_related("reviews")
        .annotate(average_rating=Avg("reviews__rating")),
        pk=pk,
    )
    form = ReviewForm()
    if request.method == "POST":
        form = ReviewForm(request.POST)
        if form.is_valid():
            review = form.save(commit=False)
            review.book = book
            review.save()
            messages.success(request, "Your review has been submitted.")
            return redirect(f"{reverse('catalog-book-detail', args=[book.pk])}#reviews")

    return render(
        request,
        "library/book_detail.html",
        {"book": book, "review_form": form},
    )


def author_detail(request, pk):
    author = get_object_or_404(Author.objects.prefetch_related("books"), pk=pk)
    return render(request, "library/author_detail.html", {"author": author})


def review_list(request):
    reviews = Review.objects.select_related("book", "book__author")
    return render(request, "library/review_list.html", {"reviews": reviews})


def review_detail(request, pk):
    review = get_object_or_404(
        Review.objects.select_related("book", "book__author"),
        pk=pk,
    )
    return render(request, "library/review_detail.html", {"review": review})


class AuthorViewSet(viewsets.ModelViewSet):
    queryset = Author.objects.prefetch_related("books")
    serializer_class = AuthorSerializer
    permission_classes = [IsAdminOrReadOnlyApiStaff]
    filterset_fields = ["country"]
    search_fields = ["name"]
    ordering_fields = ["name", "birth_year"]


class BookViewSet(viewsets.ModelViewSet):
    queryset = (
        Book.objects.select_related("author")
        .annotate(avg_rating=Avg("reviews__rating"))
        .order_by("-published_year", "title")  # annotate() drops Meta.ordering
    )
    serializer_class = BookSerializer
    permission_classes = [IsAdminOrReadOnlyApiStaff]
    filter_backends = [DjangoFilterBackend, SearchFilter, NullsLastOrderingFilter]
    filterset_fields = {
        "author": ["exact"],
        "in_stock": ["exact"],
        "published_year": ["exact", "gte", "lte"],
    }
    search_fields = ["title", "author__name"]
    ordering_fields = ["published_year", "title", "created_at", "avg_rating"]


class ReviewViewSet(viewsets.ModelViewSet):
    queryset = Review.objects.select_related("book")
    serializer_class = ReviewSerializer
    permission_classes = [IsAdminOrReadOnlyApiStaff]
    filterset_fields = ["book"]
    ordering_fields = ["rating", "created_at"]
