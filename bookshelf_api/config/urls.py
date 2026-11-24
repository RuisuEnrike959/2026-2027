from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

from library import views


urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/login/", auth_views.LoginView.as_view(), name="login"),
    path("accounts/logout/", auth_views.LogoutView.as_view(), name="logout"),
    path("accounts/signup/", views.sign_up, name="signup"),
    path("api/", include("library.urls")),
    path("", views.home, name="home"),
    path("books/", views.book_list, name="catalog-books"),
    path("books/<int:pk>/", views.book_detail, name="catalog-book-detail"),
    path("authors/<int:pk>/", views.author_detail, name="catalog-author-detail"),
    path("reviews/", views.review_list, name="catalog-reviews"),
    path("reviews/<int:pk>/", views.review_detail, name="catalog-review-detail"),
]
