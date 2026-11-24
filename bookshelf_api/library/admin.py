from django.contrib import admin
from django.utils.html import format_html

from .models import Author, Book, Review


@admin.register(Author)
class AuthorAdmin(admin.ModelAdmin):
    list_display = ["name", "country", "birth_year"]


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ["title", "author", "published_year", "in_stock", "show_on_home", "cover_preview"]
    list_filter = ["in_stock", "show_on_home"]
    search_fields = ["title", "author__name"]

    @admin.display(description="Cover")
    def cover_preview(self, book):
        if not book.cover_image:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height: 80px; width: auto;">',
            book.cover_image.url,
        )


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ["book", "reviewer_name", "rating", "created_at"]
